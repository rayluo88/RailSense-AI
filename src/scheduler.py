"""Background scheduler for periodic LTA data ingestion.

Runs as asyncio tasks inside the FastAPI lifespan. Polls LTA DataMall APIs
at configured intervals during operating hours (default 0900-2200 SGT).
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from src.config import settings
from src.db.session import SessionLocal
from src.ingestion.lta_client import ALL_TRAIN_LINES, LtaClient
from src.ingestion.writers import write_crowd_density, write_disruptions, write_facilities

logger = logging.getLogger("railsense.scheduler")

SGT = timezone(timedelta(hours=8))

# Module-level status tracking
_status: dict[str, dict] = {}


def _is_operating_hours() -> bool:
    """Check if current SGT time is within configured operating hours."""
    now_sgt = datetime.now(SGT)
    return settings.scheduler_start_hour <= now_sgt.hour < settings.scheduler_end_hour


async def _run_forever(name: str, interval_seconds: int, coro_fn):
    """Run coro_fn every interval_seconds during operating hours."""
    while True:
        if not _is_operating_hours():
            _status[name] = {**_status.get(name, {}), "state": "sleeping"}
            await asyncio.sleep(60)
            continue

        try:
            count = await coro_fn()
            _status[name] = {
                "last_run": datetime.now(SGT).isoformat(),
                "records": count,
                "state": "active",
                "error": None,
            }
            logger.info(f"[{name}] ingested {count} records")
        except asyncio.CancelledError:
            logger.info(f"[{name}] shutting down")
            raise
        except Exception as exc:
            _status[name] = {
                **_status.get(name, {}),
                "state": "error",
                "error": str(exc),
                "last_error_at": datetime.now(SGT).isoformat(),
            }
            logger.exception(f"[{name}] failed, will retry in {interval_seconds}s")

        await asyncio.sleep(interval_seconds)


async def _ingest_disruptions() -> int:
    client = LtaClient()
    disruptions = await client.get_disruptions()
    db = SessionLocal()
    try:
        return write_disruptions(db, disruptions)
    finally:
        db.close()


async def _ingest_crowd_density() -> int:
    client = LtaClient()
    all_records = []
    for line in ALL_TRAIN_LINES:
        try:
            records = await client.get_crowd_density_realtime(line)
            all_records.extend(records)
        except Exception:
            pass  # Skip failed lines
        await asyncio.sleep(0.5)  # Rate-limit courtesy

    db = SessionLocal()
    try:
        return write_crowd_density(db, all_records)
    finally:
        db.close()


async def _ingest_facilities() -> int:
    client = LtaClient()
    facilities = await client.get_facilities_maintenance()
    db = SessionLocal()
    try:
        return write_facilities(db, facilities)
    finally:
        db.close()


async def start_scheduler() -> list[asyncio.Task]:
    """Launch all periodic ingestion tasks. Returns task handles for cancellation."""
    if not settings.lta_api_key:
        logger.warning("LTA_API_KEY not set — scheduler disabled")
        return []

    tasks = [
        asyncio.create_task(_run_forever("disruptions", 300, _ingest_disruptions)),
        asyncio.create_task(_run_forever("crowd_density", 600, _ingest_crowd_density)),
        asyncio.create_task(_run_forever("facilities", 1800, _ingest_facilities)),
    ]
    logger.info(
        "Background scheduler started: disruptions=5m, crowd=10m, facilities=30m "
        f"(active {settings.scheduler_start_hour:02d}00-{settings.scheduler_end_hour:02d}00 SGT)"
    )
    return tasks


def get_scheduler_status() -> dict:
    """Return current scheduler status for the API endpoint."""
    return {
        "enabled": settings.enable_scheduler and bool(settings.lta_api_key),
        "operating_hours": f"{settings.scheduler_start_hour:02d}00-{settings.scheduler_end_hour:02d}00 SGT",
        "currently_active": _is_operating_hours(),
        "tasks": _status,
    }

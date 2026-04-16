"""Shared DB write helpers for LTA data ingestion.

Used by both the Prefect tasks (src/tasks.py) and the background scheduler
(src/scheduler.py) to avoid duplicating upsert/insert logic.
"""

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import LtaCrowdDensity, LtaDisruption, LtaFacilitiesMaintenance


def write_disruptions(db: Session, disruptions: list[dict]) -> int:
    """Upsert disruptions with MD5-based deduplication. Returns count of new records."""
    if not disruptions:
        return 0

    fetched_at = datetime.utcnow()
    inserted = 0

    for d in disruptions:
        msg_hash = hashlib.md5(
            f"{d['line_id']}|{d['direction']}|{d['affected_stations']}".encode()
        ).hexdigest()

        existing = (
            db.query(LtaDisruption)
            .filter(
                LtaDisruption.line_id == d["line_id"],
                LtaDisruption.message == msg_hash,
            )
            .order_by(LtaDisruption.timestamp.desc())
            .first()
        )
        if existing:
            existing.fetched_at = fetched_at
        else:
            db.add(LtaDisruption(
                timestamp=d["timestamp"],
                line_id=d["line_id"],
                station_id=d["affected_stations"].split("-")[0] if d["affected_stations"] else None,
                message=msg_hash,
                direction=d["direction"],
                status=d["status"],
                affected_stations=d["affected_stations"],
                free_bus=d["free_bus"],
                free_shuttle=d["free_shuttle"],
                fetched_at=fetched_at,
            ))
            inserted += 1

    db.commit()
    return inserted


def write_crowd_density(db: Session, records: list[dict]) -> int:
    """Bulk insert crowd density records. Returns count of inserted records."""
    if not records:
        return 0

    fetched_at = datetime.utcnow()
    valid = [r for r in records if r["station_code"]]
    db.bulk_save_objects([
        LtaCrowdDensity(
            timestamp=r["timestamp"],
            end_time=r["end_time"],
            station_code=r["station_code"],
            train_line=r["train_line"],
            crowd_level=r["crowd_level"],
            source=r["source"],
            fetched_at=fetched_at,
        )
        for r in valid
    ])
    db.commit()
    return len(valid)


def write_facilities(db: Session, facilities: list[dict]) -> int:
    """Replace all facilities with latest snapshot. Returns count of records."""
    if not facilities:
        return 0

    fetched_at = datetime.utcnow()
    db.query(LtaFacilitiesMaintenance).delete()
    valid = [f for f in facilities if f["station_code"]]
    db.bulk_save_objects([
        LtaFacilitiesMaintenance(
            station_code=f["station_code"],
            station_name=f["station_name"],
            train_line=f["train_line"],
            equipment_type=f["equipment_type"],
            equipment_id=f["equipment_id"],
            description=f["description"],
            fetched_at=fetched_at,
        )
        for f in valid
    ])
    db.commit()
    return len(valid)

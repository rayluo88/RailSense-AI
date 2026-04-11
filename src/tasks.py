"""Prefect tasks for scheduled data ingestion and anomaly detection."""

import asyncio
import hashlib
from datetime import datetime

import pandas as pd
from prefect import flow, task
from sqlalchemy.orm import Session

from src.db.models import (
    AnomalyEvent, LtaCrowdDensity, LtaDisruption, LtaFacilitiesMaintenance, SensorReading,
)
from src.db.session import SessionLocal
from src.detection.pipeline import DetectionPipeline
from src.ingestion.lta_client import ALL_TRAIN_LINES, LtaClient
from src.ingestion.synthetic_gen import SyntheticGenerator


@task
def ingest_synthetic_data(train_id: str, hours: int = 1):
    gen = SyntheticGenerator()
    df = gen.generate(train_id=train_id, hours=hours)

    db = SessionLocal()
    readings = [
        SensorReading(
            timestamp=row["timestamp"], train_id=row["train_id"],
            sensor_type=row["sensor_type"], value=row["value"],
            line_id=row["line_id"], station_id=row["station_id"],
        )
        for _, row in df.iterrows()
    ]
    db.bulk_save_objects(readings)
    db.commit()
    db.close()
    return len(readings)


@task
def run_detection(train_id: str, sensor_type: str):
    db = SessionLocal()
    readings = (
        db.query(SensorReading)
        .filter(SensorReading.train_id == train_id, SensorReading.sensor_type == sensor_type)
        .order_by(SensorReading.timestamp.desc())
        .limit(288)  # last 24h at 5-min intervals
        .all()
    )

    if not readings:
        db.close()
        return 0

    df = pd.DataFrame([{
        "timestamp": r.timestamp, "train_id": r.train_id,
        "sensor_type": r.sensor_type.value, "value": r.value,
        "line_id": r.line_id, "station_id": r.station_id,
    } for r in readings])

    pipeline = DetectionPipeline(methods=["zscore", "stl"])
    events = pipeline.get_anomaly_events(df)

    for event in events:
        db.add(AnomalyEvent(
            timestamp=event["timestamp"], train_id=event["train_id"],
            sensor_type=event["sensor_type"], detection_method=event["detection_method"],
            anomaly_score=event["anomaly_score"], severity=event["severity"],
            value=event["value"], line_id=event["line_id"], station_id=event["station_id"],
        ))
    db.commit()
    db.close()
    return len(events)


@task
def ingest_lta_disruptions():
    """Poll TrainServiceAlerts and upsert into lta_disruptions."""
    client = LtaClient()
    disruptions = asyncio.run(client.get_disruptions())

    if not disruptions:
        return 0

    db = SessionLocal()
    fetched_at = datetime.utcnow()
    inserted = 0

    for d in disruptions:
        # Deduplicate: same line + direction + station range within the last 5 min
        msg_hash = hashlib.md5(
            f"{d['line_id']}|{d['direction']}|{d['affected_stations']}".encode()
        ).hexdigest()

        # Store hash in the message field for dedup lookup
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
            # Update fetched_at to show it's still active
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
    db.close()
    return inserted


@task
def ingest_lta_crowd_density():
    """Poll PCDRealTime for all train lines and bulk insert into lta_crowd_density."""
    client = LtaClient()
    fetched_at = datetime.utcnow()
    all_records = []

    async def fetch_all():
        import asyncio as _asyncio
        results = []
        for line in ALL_TRAIN_LINES:
            try:
                records = await client.get_crowd_density_realtime(line)
                results.extend(records)
            except Exception:
                pass  # Skip failed lines; don't abort the whole task
            await _asyncio.sleep(0.5)  # Rate-limit courtesy delay
        return results

    all_records = asyncio.run(fetch_all())

    if not all_records:
        return 0

    db = SessionLocal()
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
        for r in all_records
        if r["station_code"]  # Skip empty station codes
    ])
    db.commit()
    db.close()
    return len(all_records)


@task
def ingest_lta_facilities():
    """Poll FacilitiesMaintenance and upsert into lta_facilities_maintenance."""
    client = LtaClient()
    facilities = asyncio.run(client.get_facilities_maintenance())
    fetched_at = datetime.utcnow()

    if not facilities:
        return 0

    db = SessionLocal()
    # Replace all facilities records with the latest snapshot (it's a point-in-time list)
    db.query(LtaFacilitiesMaintenance).delete()
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
        for f in facilities
        if f["station_code"]
    ])
    db.commit()
    db.close()
    return len(facilities)


@flow(name="railsense-ingestion-detection")
def ingestion_detection_flow():
    train_ids = ["T001", "T002", "T003", "T004", "T005"]
    sensor_types = ["vibration", "temperature", "door_cycle", "current_draw"]

    for train_id in train_ids:
        ingest_synthetic_data(train_id, hours=1)

    for train_id in train_ids:
        for sensor_type in sensor_types:
            run_detection(train_id, sensor_type)

    # LTA real data ingestion (runs after detection; independent of synthetic pipeline)
    ingest_lta_disruptions()
    ingest_lta_crowd_density()
    ingest_lta_facilities()


if __name__ == "__main__":
    ingestion_detection_flow()

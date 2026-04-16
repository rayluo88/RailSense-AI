"""Prefect tasks for scheduled data ingestion and anomaly detection."""

import asyncio
from datetime import datetime

import pandas as pd
from prefect import flow, task

from src.db.models import AnomalyEvent, SensorReading
from src.db.session import SessionLocal
from src.detection.pipeline import DetectionPipeline
from src.ingestion.lta_client import ALL_TRAIN_LINES, LtaClient
from src.ingestion.synthetic_gen import SyntheticGenerator
from src.ingestion.writers import write_crowd_density, write_disruptions, write_facilities


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
    db = SessionLocal()
    try:
        return write_disruptions(db, disruptions)
    finally:
        db.close()


@task
def ingest_lta_crowd_density():
    """Poll PCDRealTime for all train lines and bulk insert into lta_crowd_density."""
    client = LtaClient()

    async def fetch_all():
        results = []
        for line in ALL_TRAIN_LINES:
            try:
                records = await client.get_crowd_density_realtime(line)
                results.extend(records)
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return results

    all_records = asyncio.run(fetch_all())
    db = SessionLocal()
    try:
        return write_crowd_density(db, all_records)
    finally:
        db.close()


@task
def ingest_lta_facilities():
    """Poll FacilitiesMaintenance and upsert into lta_facilities_maintenance."""
    client = LtaClient()
    facilities = asyncio.run(client.get_facilities_maintenance())
    db = SessionLocal()
    try:
        return write_facilities(db, facilities)
    finally:
        db.close()


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

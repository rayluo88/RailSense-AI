from datetime import datetime

from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session

from src.api.schemas import AnomalyEventOut, SensorReadingOut
from src.db.models import AnomalyEvent, SensorReading
from src.db.session import get_db

app = FastAPI(title="RailSense-AI", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/sensors", response_model=list[SensorReadingOut])
def get_sensor_readings(
    train_id: str | None = None,
    sensor_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(SensorReading)
    if train_id:
        q = q.filter(SensorReading.train_id == train_id)
    if sensor_type:
        q = q.filter(SensorReading.sensor_type == sensor_type)
    if start:
        q = q.filter(SensorReading.timestamp >= start)
    if end:
        q = q.filter(SensorReading.timestamp <= end)
    return q.order_by(SensorReading.timestamp.desc()).limit(limit).all()


@app.get("/api/anomalies", response_model=list[AnomalyEventOut])
def get_anomalies(
    severity: str | None = None,
    train_id: str | None = None,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(AnomalyEvent)
    if severity:
        q = q.filter(AnomalyEvent.severity == severity)
    if train_id:
        q = q.filter(AnomalyEvent.train_id == train_id)
    return q.order_by(AnomalyEvent.timestamp.desc()).limit(limit).all()

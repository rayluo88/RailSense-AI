from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from src.agent.provider import AnomalyContext, get_provider
from src.api.schemas import AgentAssessmentOut, AnomalyEventOut, SensorReadingOut
from src.config import settings
from src.dashboard.routes import router as dashboard_router
from src.db.models import AgentAssessment as AgentAssessmentModel, AnomalyEvent, SensorReading
from src.db.session import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="RailSense-AI", version="0.1.0", lifespan=lifespan)

# Static files and Jinja2 dashboard
app.mount("/static", StaticFiles(directory="src/static"), name="static")


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


@app.post("/api/assess/{anomaly_event_id}", response_model=AgentAssessmentOut)
async def assess_anomaly(anomaly_event_id: int, db: Session = Depends(get_db)):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Anomaly event not found")

    recent = (
        db.query(SensorReading)
        .filter(SensorReading.train_id == event.train_id, SensorReading.sensor_type == event.sensor_type)
        .filter(SensorReading.timestamp <= event.timestamp)
        .order_by(SensorReading.timestamp.desc())
        .limit(5)
        .all()
    )

    context = AnomalyContext(
        timestamp=event.timestamp,
        train_id=event.train_id,
        line_id=event.line_id,
        station_id=event.station_id,
        sensor_type=event.sensor_type.value,
        value=event.value,
        anomaly_score=event.anomaly_score,
        detection_methods=[event.detection_method],
        is_peak_hour=event.timestamp.hour in {7, 8, 9, 17, 18, 19},
        recent_history=[{"timestamp": str(r.timestamp), "value": r.value} for r in recent],
        correlated_sensors=[],
    )

    provider = get_provider(settings.llm_provider)
    assessment = await provider.analyze_anomaly(context)

    db_assessment = AgentAssessmentModel(
        anomaly_event_id=event.id,
        llm_provider=settings.llm_provider,
        root_cause=assessment.root_cause,
        severity_override=assessment.severity,
        recommended_action=assessment.recommended_action,
        reasoning=assessment.reasoning,
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment


@app.get("/api/assessments", response_model=list[AgentAssessmentOut])
def get_assessments(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(AgentAssessmentModel)
        .order_by(AgentAssessmentModel.created_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/compare")
def run_comparison(
    sensor_type: str = "temperature",
    hours: int = 48,
):
    from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario
    from src.detection.compare import compare_detectors

    gen = SyntheticGenerator(seed=99)
    scenario = AnomalyScenario(
        sensor_types=[sensor_type], start_hour=12, duration_hours=2, magnitude=4.0
    )
    df = gen.generate(train_id="COMPARE", hours=hours, anomalies=[scenario])
    filtered = df[df["sensor_type"] == sensor_type].reset_index(drop=True)
    return compare_detectors(filtered)


# Dashboard routes (must be last to avoid overriding /api/* routes)
app.include_router(dashboard_router)

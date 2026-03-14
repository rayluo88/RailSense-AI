from datetime import datetime

from pydantic import BaseModel


class SensorReadingOut(BaseModel):
    id: int
    timestamp: datetime
    train_id: str
    sensor_type: str
    value: float
    line_id: str
    station_id: str

    model_config = {"from_attributes": True}


class AnomalyEventOut(BaseModel):
    id: int
    timestamp: datetime
    train_id: str
    sensor_type: str
    detection_method: str
    anomaly_score: float
    severity: str
    value: float
    line_id: str
    station_id: str

    model_config = {"from_attributes": True}


class AgentAssessmentOut(BaseModel):
    id: int
    anomaly_event_id: int
    llm_provider: str
    root_cause: str
    severity_override: str | None
    recommended_action: str
    reasoning: str
    created_at: datetime

    model_config = {"from_attributes": True}

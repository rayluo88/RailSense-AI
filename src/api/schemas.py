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


class DisruptionOut(BaseModel):
    id: int
    timestamp: datetime
    line_id: str
    station_id: str | None
    direction: str | None
    status: str | None
    affected_stations: str | None
    free_bus: str | None
    free_shuttle: str | None

    model_config = {"from_attributes": True}


class CrowdDensityOut(BaseModel):
    id: int
    timestamp: datetime
    end_time: datetime | None
    station_code: str
    train_line: str
    crowd_level: str
    source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class FacilitiesMaintenanceOut(BaseModel):
    id: int
    station_code: str
    station_name: str
    train_line: str
    equipment_type: str
    equipment_id: str | None
    description: str | None
    fetched_at: datetime

    model_config = {"from_attributes": True}

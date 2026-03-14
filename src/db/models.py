import enum
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class SensorType(str, enum.Enum):
    VIBRATION = "vibration"
    TEMPERATURE = "temperature"
    DOOR_CYCLE = "door_cycle"
    CURRENT_DRAW = "current_draw"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    train_id = Column(String(20), nullable=False, index=True)
    sensor_type = Column(Enum(SensorType), nullable=False)
    value = Column(Float, nullable=False)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_sensor_readings_train_time", "train_id", "timestamp"),
    )


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    train_id = Column(String(20), nullable=False)
    sensor_type = Column(Enum(SensorType), nullable=False)
    detection_method = Column(String(30), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    value = Column(Float, nullable=False)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20), nullable=False)

    assessments = relationship("AgentAssessment", back_populates="anomaly_event")


class AgentAssessment(Base):
    __tablename__ = "agent_assessments"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(Integer, ForeignKey("anomaly_events.id"), nullable=False)
    llm_provider = Column(String(20), nullable=False)
    root_cause = Column(Text, nullable=False)
    severity_override = Column(Enum(Severity))
    recommended_action = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    anomaly_event = relationship("AnomalyEvent", back_populates="assessments")


class LtaDisruption(Base):
    __tablename__ = "lta_disruptions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20))
    message = Column(Text, nullable=False)
    direction = Column(String(50))

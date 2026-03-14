from src.db.models import SensorType, Severity, SensorReading, AnomalyEvent


def test_sensor_type_enum():
    assert SensorType.VIBRATION.value == "vibration"
    assert len(SensorType) == 4


def test_severity_enum():
    assert Severity.CRITICAL.value == "critical"
    assert len(Severity) == 3


def test_sensor_reading_columns():
    cols = {c.name for c in SensorReading.__table__.columns}
    assert cols == {"id", "timestamp", "train_id", "sensor_type", "value", "line_id", "station_id"}


def test_anomaly_event_columns():
    cols = {c.name for c in AnomalyEvent.__table__.columns}
    assert "anomaly_score" in cols
    assert "detection_method" in cols

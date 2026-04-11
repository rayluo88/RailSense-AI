from datetime import datetime

from src.agent.provider import AnomalyContext, AgentAssessment, get_provider
from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def test_anomaly_context_creation():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001",
        line_id="NSL",
        station_id="NS1",
        sensor_type="vibration",
        value=0.8,
        anomaly_score=0.92,
        detection_methods=["zscore", "isolation_forest"],
        is_peak_hour=True,
        recent_history=[],
        correlated_sensors=[],
    )
    assert ctx.is_peak_hour is True
    assert ctx.anomaly_score == 0.92


def test_agent_assessment_creation():
    assessment = AgentAssessment(
        root_cause="Bearing wear",
        severity="critical",
        recommended_action="Immediate inspection",
        reasoning="High vibration during peak hours",
    )
    assert assessment.severity == "critical"


def test_get_provider_deepseek():
    provider = get_provider("deepseek")
    assert hasattr(provider, "analyze_anomaly")


def test_get_provider_unknown():
    try:
        get_provider("unknown")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_prompt_template_formats():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001", line_id="NSL", station_id="NS1",
        sensor_type="vibration", value=0.8, anomaly_score=0.92,
        detection_methods=["zscore"], is_peak_hour=True,
        recent_history=[], correlated_sensors=[],
    )
    prompt = USER_PROMPT_TEMPLATE.format(
        train_id=ctx.train_id, line_id=ctx.line_id, station_id=ctx.station_id,
        timestamp=ctx.timestamp.isoformat(), sensor_type=ctx.sensor_type,
        value=ctx.value, anomaly_score=ctx.anomaly_score,
        detection_methods=", ".join(ctx.detection_methods),
        is_peak_hour=ctx.is_peak_hour, recent_history="[]", correlated_sensors="[]",
        active_disruptions="None", crowd_levels="None", facilities_issues="None",
    )
    assert "T001" in prompt
    assert "vibration" in prompt
    assert "LTA Operational Context" in prompt
    assert SYSTEM_PROMPT.startswith("You are a railway")


def test_anomaly_context_lta_fields_default_empty():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001", line_id="NSL", station_id="NS1",
        sensor_type="vibration", value=0.8, anomaly_score=0.92,
        detection_methods=["zscore"], is_peak_hour=True,
        recent_history=[], correlated_sensors=[],
    )
    assert ctx.active_disruptions == []
    assert ctx.crowd_levels == []
    assert ctx.facilities_issues == []


def test_anomaly_context_lta_fields_populated():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001", line_id="NSL", station_id="NS1",
        sensor_type="vibration", value=0.8, anomaly_score=0.92,
        detection_methods=["zscore"], is_peak_hour=True,
        recent_history=[], correlated_sensors=[],
        active_disruptions=[{"line": "NSL", "status": "2", "stations": "NS1-NS5"}],
        crowd_levels=[{"station": "NS1", "level": "h"}],
        facilities_issues=[{"station": "NS3", "equipment": "B1L01", "desc": "Lift to platform"}],
    )
    assert len(ctx.active_disruptions) == 1
    assert ctx.active_disruptions[0]["status"] == "2"
    assert ctx.crowd_levels[0]["level"] == "h"

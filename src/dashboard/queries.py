"""Database query functions for the Jinja2 dashboard."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.db.models import AnomalyEvent, SensorReading

TOTAL_FLEET = 200  # Approximate MRT fleet across NSL, EWL, CCL, DTL, NEL

LINE_INFO = {
    "NSL": "North South Line",
    "EWL": "East West Line",
    "CCL": "Circle Line",
    "DTL": "Downtown Line",
    "NEL": "North East Line",
}


def get_overview_data(db: Session) -> dict:
    anomalies = (
        db.query(AnomalyEvent)
        .order_by(AnomalyEvent.timestamp.desc())
        .limit(500)
        .all()
    )

    critical = [a for a in anomalies if a.severity.value == "critical"]
    warnings = [a for a in anomalies if a.severity.value == "warning"]
    affected_trains = set(a.train_id for a in anomalies)
    health = round((TOTAL_FLEET - len(affected_trains)) / TOTAL_FLEET * 100)

    # Per-line health
    line_counts: dict[str, int] = {}
    for a in anomalies:
        lid = a.line_id.upper()
        line_counts[lid] = line_counts.get(lid, 0) + 1
    max_count = max(line_counts.values()) if line_counts else 1

    line_health = []
    for code, name in LINE_INFO.items():
        count = line_counts.get(code, 0)
        pct = round(100 - (count / max(max_count, 1)) * 30) if count > 0 else 100
        if pct >= 95:
            bar_color = "var(--healthy)"
            pct_color = "var(--healthy)"
        elif pct >= 80:
            bar_color = "var(--warning)"
            pct_color = "var(--warning)"
        else:
            bar_color = f"linear-gradient(90deg, var(--warning), var(--{code.lower()}-{'red' if code == 'NSL' else 'green' if code == 'EWL' else 'orange' if code == 'CCL' else 'blue' if code == 'DTL' else 'purple'}))"
            pct_color = "var(--warning)"
        line_health.append({
            "code": code,
            "name": name,
            "pct": pct,
            "bar_color": bar_color,
            "pct_color": pct_color,
        })

    # Active alerts — critical first, then by score
    sorted_anomalies = sorted(
        anomalies,
        key=lambda a: (0 if a.severity.value == "critical" else 1, -a.anomaly_score),
    )

    return {
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "affected_trains": len(affected_trains),
        "health": health,
        "line_health": line_health,
        "active_alerts": sorted_anomalies[:5],
        "recent_anomalies": anomalies[:10],
    }


def get_sensor_data(
    db: Session,
    train_id: str = "T001",
    sensor_type: str = "vibration",
) -> dict:
    readings = (
        db.query(SensorReading)
        .filter(
            SensorReading.train_id == train_id,
            SensorReading.sensor_type == sensor_type,
        )
        .order_by(SensorReading.timestamp.asc())
        .all()
    )

    anomalies = (
        db.query(AnomalyEvent)
        .filter(
            AnomalyEvent.train_id == train_id,
            AnomalyEvent.sensor_type == sensor_type,
        )
        .order_by(AnomalyEvent.timestamp.desc())
        .limit(200)
        .all()
    )

    values = [r.value for r in readings]
    if values:
        import statistics
        mean = round(statistics.mean(values), 2)
        std = round(statistics.stdev(values), 3) if len(values) > 1 else 0
        max_val = round(max(values), 2)
    else:
        mean = std = max_val = 0

    # Prepare chart data as JSON-serializable lists
    chart_timestamps = [r.timestamp.isoformat() for r in readings]
    chart_values = [r.value for r in readings]
    anom_timestamps = [a.timestamp.isoformat() for a in anomalies]
    anom_values = [a.value for a in anomalies]
    anom_scores = [a.anomaly_score for a in anomalies]
    anom_severities = [a.severity.value for a in anomalies]

    return {
        "train_id": train_id,
        "sensor_type": sensor_type,
        "data_points": len(readings),
        "mean": mean,
        "std": std,
        "max_val": max_val,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "chart_timestamps": chart_timestamps,
        "chart_values": chart_values,
        "anom_timestamps": anom_timestamps,
        "anom_values": anom_values,
        "anom_scores": anom_scores,
        "anom_severities": anom_severities,
    }


def get_alert_feed_data(db: Session, severity: str | None = None) -> dict:
    q = (
        db.query(AnomalyEvent)
        .options(joinedload(AnomalyEvent.assessments))
        .order_by(AnomalyEvent.timestamp.desc())
    )
    if severity:
        q = q.filter(AnomalyEvent.severity == severity)
    alerts = q.limit(200).all()

    all_alerts = (
        db.query(AnomalyEvent)
        .order_by(AnomalyEvent.timestamp.desc())
        .limit(200)
        .all()
    )
    total = len(all_alerts)
    crit = sum(1 for a in all_alerts if a.severity.value == "critical")
    warn = sum(1 for a in all_alerts if a.severity.value == "warning")

    # Sort: critical first, then by score
    alerts_sorted = sorted(
        alerts,
        key=lambda a: (0 if a.severity.value == "critical" else 1, -a.anomaly_score),
    )

    return {
        "alerts": alerts_sorted,
        "total": total,
        "critical_count": crit,
        "warning_count": warn,
        "severity_filter": severity,
    }

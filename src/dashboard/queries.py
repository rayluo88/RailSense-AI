"""Database query functions for the Jinja2 dashboard."""

from __future__ import annotations

import re

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.db.models import AnomalyEvent, LtaCrowdDensity, LtaDisruption, LtaFacilitiesMaintenance, SensorReading

TOTAL_FLEET = 200  # Approximate MRT fleet across NSL, EWL, CCL, DTL, NEL

# Singapore MRT/LRT station code → name mapping
STATION_NAMES: dict[str, str] = {
    # North South Line (NSL)
    "NS1": "Jurong East", "NS2": "Bukit Batok", "NS3": "Bukit Gombak",
    "NS4": "Choa Chu Kang", "NS5": "Yew Tee", "NS7": "Kranji",
    "NS8": "Marsiling", "NS9": "Woodlands", "NS10": "Admiralty",
    "NS11": "Sembawang", "NS12": "Canberra", "NS13": "Yishun",
    "NS14": "Khatib", "NS15": "Yio Chu Kang", "NS16": "Ang Mo Kio",
    "NS17": "Bishan", "NS18": "Braddell", "NS19": "Toa Payoh",
    "NS20": "Novena", "NS21": "Newton", "NS22": "Orchard",
    "NS23": "Somerset", "NS24": "Dhoby Ghaut", "NS25": "City Hall",
    "NS26": "Raffles Place", "NS27": "Marina Bay", "NS28": "Marina South Pier",
    # East West Line (EWL)
    "EW1": "Pasir Ris", "EW2": "Tampines", "EW3": "Simei",
    "EW4": "Tanah Merah", "EW5": "Bedok", "EW6": "Kembangan",
    "EW7": "Eunos", "EW8": "Paya Lebar", "EW9": "Aljunied",
    "EW10": "Kallang", "EW11": "Lavender", "EW12": "Bugis",
    "EW13": "City Hall", "EW14": "Raffles Place", "EW15": "Tanjong Pagar",
    "EW16": "Outram Park", "EW17": "Tiong Bahru", "EW18": "Redhill",
    "EW19": "Queenstown", "EW20": "Commonwealth", "EW21": "Buona Vista",
    "EW22": "Dover", "EW23": "Clementi", "EW24": "Jurong East",
    "EW25": "Chinese Garden", "EW26": "Lakeside", "EW27": "Boon Lay",
    "EW28": "Pioneer", "EW29": "Joo Koon", "EW30": "Gul Circle",
    "EW31": "Tuas Crescent", "EW32": "Tuas West Road", "EW33": "Tuas Link",
    # Changi branch
    "CG1": "Expo", "CG2": "Changi Airport",
    # North East Line (NEL)
    "NE1": "HarbourFront", "NE3": "Outram Park", "NE4": "Chinatown",
    "NE5": "Clarke Quay", "NE6": "Dhoby Ghaut", "NE7": "Little India",
    "NE8": "Farrer Park", "NE9": "Boon Keng", "NE10": "Potong Pasir",
    "NE11": "Woodleigh", "NE12": "Serangoon", "NE13": "Kovan",
    "NE14": "Hougang", "NE15": "Buangkok", "NE16": "Sengkang",
    "NE17": "Punggol",
    # Circle Line (CCL)
    "CC1": "Dhoby Ghaut", "CC2": "Bras Basah", "CC3": "Esplanade",
    "CC4": "Promenade", "CC5": "Nicoll Highway", "CC6": "Stadium",
    "CC7": "Mountbatten", "CC8": "Dakota", "CC9": "Paya Lebar",
    "CC10": "MacPherson", "CC11": "Tai Seng", "CC12": "Bartley",
    "CC13": "Serangoon", "CC14": "Lorong Chuan", "CC15": "Bishan",
    "CC16": "Marymount", "CC17": "Caldecott", "CC19": "Botanic Gardens",
    "CC20": "Farrer Road", "CC21": "Holland Village", "CC22": "Buona Vista",
    "CC23": "one-north", "CC24": "Kent Ridge", "CC25": "Haw Par Villa",
    "CC26": "Pasir Panjang", "CC27": "Labrador Park", "CC28": "Telok Blangah",
    "CC29": "HarbourFront",
    # Circle Line Extension (CEL)
    "CE1": "Bayfront", "CE2": "Marina Bay",
    # Downtown Line (DTL)
    "DT1": "Bukit Panjang", "DT2": "Cashew", "DT3": "Hillview",
    "DT5": "Beauty World", "DT6": "King Albert Park",
    "DT7": "Sixth Avenue", "DT8": "Tan Kah Kee", "DT9": "Botanic Gardens",
    "DT10": "Stevens", "DT11": "Newton", "DT12": "Little India",
    "DT13": "Rochor", "DT14": "Bugis", "DT15": "Promenade",
    "DT16": "Bayfront", "DT17": "Downtown", "DT18": "Telok Ayer",
    "DT19": "Chinatown", "DT20": "Fort Canning", "DT21": "Bencoolen",
    "DT22": "Jalan Besar", "DT23": "Bendemeer", "DT24": "Geylang Bahru",
    "DT25": "Mattar", "DT26": "MacPherson", "DT27": "Ubi",
    "DT28": "Kaki Bukit", "DT29": "Bedok North", "DT30": "Bedok Reservoir",
    "DT31": "Tampines West", "DT32": "Tampines", "DT33": "Tampines East",
    "DT34": "Upper Changi", "DT35": "Expo",
    # Thomson-East Coast Line (TEL)
    "TE1": "Woodlands North", "TE2": "Woodlands", "TE3": "Woodlands South",
    "TE4": "Springleaf", "TE5": "Lentor", "TE6": "Mayflower",
    "TE7": "Bright Hill", "TE8": "Upper Thomson", "TE9": "Caldecott",
    "TE11": "Stevens", "TE12": "Napier", "TE13": "Orchard Boulevard",
    "TE14": "Orchard", "TE15": "Great World", "TE16": "Havelock",
    "TE17": "Outram Park", "TE18": "Maxwell", "TE19": "Shenton Way",
    "TE20": "Marina Bay", "TE22": "Gardens by the Bay",
    "TE23": "Tanjong Rhu", "TE24": "Katong Park", "TE25": "Tanjong Katong",
    "TE26": "Marine Parade", "TE27": "Marine Terrace", "TE28": "Siglap",
    "TE29": "Bayshore",
    # Bukit Panjang LRT (BPL)
    "BP1": "Choa Chu Kang", "BP2": "South View", "BP3": "Keat Hong",
    "BP4": "Teck Whye", "BP5": "Phoenix", "BP6": "Bukit Panjang",
    "BP7": "Petir", "BP8": "Pending", "BP9": "Bangkit",
    "BP10": "Fajar", "BP11": "Segar", "BP12": "Jelapang",
    "BP13": "Senja", "BP14": "Ten Mile Junction",
    # Sengkang LRT (SLRT)
    "SE1": "Sengkang", "SE2": "Compassvale", "SE3": "Rumbia",
    "SE4": "Bakau", "SE5": "Kangkar",
    "SW1": "Sengkang", "SW2": "Thanggam", "SW3": "Fernvale",
    "SW4": "Layar", "SW5": "Tongkang", "SW6": "Renjong",
    "SW7": "Cheng Lim", "SW8": "Farmway",
    # Punggol LRT (PLRT)
    "PE1": "Punggol", "PE2": "Meridian", "PE3": "Coral Edge",
    "PE4": "Riviera", "PE5": "Kadaloor", "PE6": "Oasis", "PE7": "Damai",
    "PW1": "Punggol", "PW3": "Sam Kee", "PW4": "Punggol Point",
    "PW5": "Samudera", "PW6": "Nibong", "PW7": "Sumang",
}

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


def get_operations_data(db: Session) -> dict:
    """Aggregate LTA real-time operational data for the operations dashboard page."""
    disruptions = (
        db.query(LtaDisruption)
        .order_by(LtaDisruption.timestamp.desc())
        .limit(50)
        .all()
    )

    # Latest crowd snapshot per line: get the most recent fetched_at, then filter
    latest_crowd = (
        db.query(LtaCrowdDensity)
        .order_by(LtaCrowdDensity.fetched_at.desc())
        .limit(200)
        .all()
    )

    # Deduplicate to one entry per (train_line, station_code) — latest only
    seen: set[tuple[str, str]] = set()
    crowd_deduped = []
    for c in latest_crowd:
        key = (c.train_line, c.station_code)
        if key not in seen:
            seen.add(key)
            crowd_deduped.append(c)

    def _station_sort_key(c) -> int:
        """Sort by the trailing numeric digits of the station code (e.g. EW10 → 10, P2 → 2)."""
        m = re.search(r"(\d+)$", c.station_code)
        return int(m.group(1)) if m else 0

    # Group crowd by line, sorted numerically by station number within each line
    crowd_by_line: dict[str, list] = {}
    for c in crowd_deduped:
        crowd_by_line.setdefault(c.train_line, []).append(c)
    for line in crowd_by_line:
        crowd_by_line[line].sort(key=_station_sort_key)

    facilities = (
        db.query(LtaFacilitiesMaintenance)
        .order_by(LtaFacilitiesMaintenance.fetched_at.desc())
        .all()
    )

    major_disruptions = [d for d in disruptions if d.status == "2"]

    return {
        "disruptions": disruptions,
        "major_disruption_count": len(major_disruptions),
        "crowd_by_line": crowd_by_line,
        "facilities": facilities,
        "has_lta_data": bool(disruptions or latest_crowd or facilities),
        "station_names": STATION_NAMES,
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

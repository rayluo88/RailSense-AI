"""Generate a compelling demo dataset with realistic failure scenarios.

Creates 30 days of sensor data across 5 train units on 3 MRT lines,
embedding three distinct failure patterns that showcase the detection
pipeline's ability to catch gradual degradation and sudden faults.

Usage:
    python scripts/demo_seed.py
"""

from src.db.models import AnomalyEvent, SensorReading
from src.db.session import Base, SessionLocal, engine
from src.detection.pipeline import DetectionPipeline
from src.ingestion.synthetic_gen import AnomalyScenario, SyntheticGenerator

# --- Configuration -----------------------------------------------------------

HOURS = 720  # 30 days

TRAIN_UNITS = ["T001", "T002", "T003", "T004", "T005"]

LINES = {
    "T001": "NSL",
    "T002": "NSL",
    "T003": "NSL",
    "T004": "EWL",
    "T005": "CCL",
}

STATIONS = {
    "T001": "NS1",   # Jurong East
    "T002": "NS9",   # Woodlands
    "T003": "NS14",  # Khatib
    "T004": "EW12",  # Bugis
    "T005": "CC3",   # Esplanade
}

# Three failure scenarios designed to demonstrate different detection strengths:
#
# 1. Bearing degradation (T001, NSL) — gradual vibration increase over the
#    last 5 days.  Best caught by STL/Prophet (trend component) and ensemble
#    agreement.
#
# 2. Door mechanism wear (T003, NSL) — door cycle time slowly rises over
#    the last 10 days.  A long-horizon gradual anomaly that challenges
#    Z-Score but is well-suited for Prophet forecast residuals.
#
# 3. Electrical fault (T005, CCL) — sudden current draw spike on day 28.
#    A sharp transient easily flagged by Z-Score and Isolation Forest.

SCENARIOS = {
    "T001": [
        AnomalyScenario(
            sensor_types=["vibration"],
            start_hour=600,       # day 25
            duration_hours=120,   # through day 30
            magnitude=4.0,
            gradual=True,
        ),
    ],
    "T003": [
        AnomalyScenario(
            sensor_types=["door_cycle"],
            start_hour=480,       # day 20
            duration_hours=240,   # through day 30
            magnitude=3.0,
            gradual=True,
        ),
    ],
    "T005": [
        AnomalyScenario(
            sensor_types=["current_draw"],
            start_hour=672,       # day 28
            duration_hours=2,
            magnitude=6.0,
            gradual=False,
        ),
    ],
}


def demo_seed():
    """Seed the database with 30-day demo data and run detection."""
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Clear existing data
    db.query(AnomalyEvent).delete()
    db.query(SensorReading).delete()
    db.commit()

    gen = SyntheticGenerator(seed=42)
    pipeline = DetectionPipeline(methods=["zscore", "stl"])

    total_readings = 0
    total_anomalies = 0

    for train_id in TRAIN_UNITS:
        print(f"[seed] Generating {HOURS}h of data for {train_id} ({LINES[train_id]})...")
        df = gen.generate(
            train_id=train_id,
            hours=HOURS,
            line_id=LINES[train_id],
            station_id=STATIONS[train_id],
            anomalies=SCENARIOS.get(train_id, []),
        )

        # Persist sensor readings
        readings = [
            SensorReading(
                timestamp=row["timestamp"],
                train_id=row["train_id"],
                sensor_type=row["sensor_type"],
                value=row["value"],
                line_id=row["line_id"],
                station_id=row["station_id"],
            )
            for _, row in df.iterrows()
        ]
        db.bulk_save_objects(readings)
        db.commit()
        total_readings += len(readings)
        print(f"  -> {len(readings):,} readings inserted")

        # Run detection per sensor type to get anomaly events
        train_anomalies = 0
        for sensor_type in df["sensor_type"].unique():
            sensor_df = df[df["sensor_type"] == sensor_type].copy()
            events = pipeline.get_anomaly_events(sensor_df)
            for evt in events:
                db.add(AnomalyEvent(
                    timestamp=evt["timestamp"],
                    train_id=evt["train_id"],
                    sensor_type=evt["sensor_type"],
                    detection_method=evt["detection_method"],
                    anomaly_score=evt["anomaly_score"],
                    severity=evt["severity"],
                    value=evt["value"],
                    line_id=evt["line_id"],
                    station_id=evt["station_id"],
                ))
            train_anomalies += len(events)
        db.commit()
        total_anomalies += train_anomalies
        print(f"  -> {train_anomalies} anomaly events detected")

    db.close()

    # Summary
    print("\n" + "=" * 60)
    print("Demo seed complete")
    print(f"  Train units:     {len(TRAIN_UNITS)}")
    print(f"  Time span:       {HOURS} hours ({HOURS // 24} days)")
    print(f"  Total readings:  {total_readings:,}")
    print(f"  Anomaly events:  {total_anomalies}")
    print("=" * 60)
    print("\nFailure scenarios embedded:")
    print("  1. T001 NSL — Bearing degradation (vibration, days 25-30, gradual)")
    print("  2. T003 NSL — Door mechanism wear (door_cycle, days 20-30, gradual)")
    print("  3. T005 CCL — Electrical fault (current_draw, day 28, spike)")


if __name__ == "__main__":
    demo_seed()

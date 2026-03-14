"""Seed the database with synthetic sensor data for demo purposes."""

from src.db.models import SensorReading
from src.db.session import SessionLocal, engine, Base
from src.ingestion.synthetic_gen import AnomalyScenario, SyntheticGenerator

TRAIN_UNITS = ["T001", "T002", "T003", "T004", "T005"]
LINES = {"T001": "NSL", "T002": "NSL", "T003": "EWL", "T004": "EWL", "T005": "CCL"}
STATIONS = {"T001": "NS1", "T002": "NS9", "T003": "EW4", "T004": "EW12", "T005": "CC3"}

SCENARIOS = {
    "T002": [
        AnomalyScenario(sensor_types=["vibration", "temperature"], start_hour=36, duration_hours=4, magnitude=3.5),
    ],
    "T004": [
        AnomalyScenario(sensor_types=["door_cycle"], start_hour=0, duration_hours=72, magnitude=2.5, gradual=True),
    ],
    "T005": [
        AnomalyScenario(sensor_types=["current_draw"], start_hour=48, duration_hours=1, magnitude=5.0),
    ],
}


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Clear existing data
    db.query(SensorReading).delete()
    db.commit()

    gen = SyntheticGenerator(seed=42)

    for train_id in TRAIN_UNITS:
        print(f"Generating data for {train_id}...")
        df = gen.generate(
            train_id=train_id,
            hours=72,
            line_id=LINES[train_id],
            station_id=STATIONS[train_id],
            anomalies=SCENARIOS.get(train_id, []),
        )

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
        print(f"  Inserted {len(readings)} readings")

    db.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()

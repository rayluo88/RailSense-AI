import pandas as pd

from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario


def test_generator_produces_dataframe():
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_generator_has_all_sensor_types():
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    expected = {"vibration", "temperature", "door_cycle", "current_draw"}
    assert set(df["sensor_type"].unique()) == expected


def test_generator_follows_daily_pattern():
    """Peak hours should have higher baseline values than off-peak."""
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    temp = df[df["sensor_type"] == "temperature"]
    peak = temp[(temp["timestamp"].dt.hour >= 7) & (temp["timestamp"].dt.hour <= 9)]
    offpeak = temp[(temp["timestamp"].dt.hour >= 1) & (temp["timestamp"].dt.hour <= 4)]
    assert peak["value"].mean() > offpeak["value"].mean()


def test_anomaly_injection():
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["vibration", "temperature"],
        start_hour=12,
        duration_hours=2,
        magnitude=3.0,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    assert "is_anomaly" in df.columns
    assert df["is_anomaly"].sum() > 0


def test_correlated_anomaly():
    """Bearing failure should show in both vibration AND temperature."""
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["vibration", "temperature"],
        start_hour=12,
        duration_hours=2,
        magnitude=3.0,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    anomaly_window = df[df["is_anomaly"]]
    anomaly_sensors = anomaly_window["sensor_type"].unique()
    assert "vibration" in anomaly_sensors
    assert "temperature" in anomaly_sensors


def test_gradual_degradation():
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["door_cycle"],
        start_hour=0,
        duration_hours=24,
        magnitude=2.0,
        gradual=True,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    door = df[df["sensor_type"] == "door_cycle"].sort_values("timestamp")
    first_quarter = door.head(len(door) // 4)["value"].mean()
    last_quarter = door.tail(len(door) // 4)["value"].mean()
    assert last_quarter > first_quarter

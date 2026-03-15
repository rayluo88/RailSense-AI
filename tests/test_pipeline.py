import pandas as pd
import numpy as np

from src.detection.pipeline import DetectionPipeline


def _make_test_data(n=576):
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    return pd.DataFrame({
        "timestamp": timestamps,
        "train_id": "T001",
        "sensor_type": "vibration",
        "value": rng.normal(0.3, 0.05, n),
        "line_id": "NSL",
        "station_id": "NS1",
    })


def test_pipeline_runs_zscore():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore"])
    results = pipeline.run(df)
    assert "anomaly_score" in results.columns
    assert "detection_method" in results.columns


def test_pipeline_runs_multiple_methods():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore", "stl"])
    results = pipeline.run(df)
    assert "ensemble_score" in results.columns
    assert "ensemble_severity" in results.columns


def test_pipeline_filters_warnings_and_above():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore"])
    anomalies = pipeline.get_anomaly_events(df)
    assert isinstance(anomalies, list)
    for event in anomalies:
        assert event["severity"] in ("warning", "critical")

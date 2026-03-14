import numpy as np
import pandas as pd

from src.detection.isolation_forest import IsolationForestDetector


def _make_multivariate(n=500):
    """4-sensor data with one multivariate outlier at row 250."""
    rng = np.random.default_rng(42)
    data = {
        "timestamp": pd.date_range("2026-03-01", periods=n, freq="5min"),
        "vibration": rng.normal(0.3, 0.05, n),
        "temperature": rng.normal(35, 2, n),
        "door_cycle": rng.normal(2500, 100, n),
        "current_draw": rng.normal(150, 15, n),
    }
    # Inject correlated anomaly
    data["vibration"][250] = 0.8
    data["temperature"][250] = 55.0
    return pd.DataFrame(data)


def test_detects_multivariate_outlier():
    df = _make_multivariate()
    detector = IsolationForestDetector(contamination=0.02)
    results = detector.detect(df)
    assert results.iloc[250]["anomaly_score"] > 0.5


def test_output_has_required_columns():
    df = _make_multivariate()
    detector = IsolationForestDetector()
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert "severity" in results.columns
    assert "detection_method" in results.columns


def test_scores_normalized():
    df = _make_multivariate()
    detector = IsolationForestDetector()
    results = detector.detect(df)
    assert results["anomaly_score"].min() >= 0.0
    assert results["anomaly_score"].max() <= 1.0

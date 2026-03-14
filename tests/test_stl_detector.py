import numpy as np
import pandas as pd

from src.detection.stl_detector import STLDetector


def _make_seasonal_series(n=576, anomaly_at=400):
    """2 days of data (5-min intervals) with daily seasonality and one anomaly."""
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    # Daily seasonal pattern
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 288)
    noise = rng.normal(0, 0.5, n)
    values = 35.0 + seasonal + noise
    if anomaly_at is not None:
        values[anomaly_at] += 15.0
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_detects_anomaly_in_seasonal_data():
    df = _make_seasonal_series(anomaly_at=400)
    detector = STLDetector(period=288, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    assert results.iloc[400]["severity"] in ("warning", "critical")


def test_clean_seasonal_data_few_false_positives():
    df = _make_seasonal_series(anomaly_at=None)
    detector = STLDetector(period=288, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    flagged = results["severity"].dropna()
    assert len(flagged) < len(results) * 0.05


def test_output_columns():
    df = _make_seasonal_series()
    detector = STLDetector(period=288)
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert "detection_method" in results.columns
    assert (results["detection_method"] == "stl").all()

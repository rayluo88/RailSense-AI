import numpy as np
import pandas as pd

from src.detection.prophet_detector import ProphetDetector


def _make_seasonal_series(n=576, anomaly_at=400):
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 288)
    noise = rng.normal(0, 0.5, n)
    values = 35.0 + seasonal + noise
    if anomaly_at is not None:
        values[anomaly_at] += 15.0
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_detects_anomaly():
    df = _make_seasonal_series(anomaly_at=400)
    detector = ProphetDetector(threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    assert results.iloc[400]["severity"] in ("warning", "critical")


def test_output_columns():
    df = _make_seasonal_series()
    detector = ProphetDetector()
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert (results["detection_method"] == "prophet").all()


def test_scores_normalized():
    df = _make_seasonal_series()
    detector = ProphetDetector()
    results = detector.detect(df)
    assert results["anomaly_score"].min() >= 0.0
    assert results["anomaly_score"].max() <= 1.0

import numpy as np
import pandas as pd

from src.detection.zscore import ZScoreDetector


def _make_series(n=1000, spike_at=500, spike_magnitude=5.0):
    """Normal series with one spike."""
    rng = np.random.default_rng(42)
    values = rng.normal(0.3, 0.05, n)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    if spike_at is not None:
        values[spike_at] = 0.3 + 0.05 * spike_magnitude
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_no_anomalies_in_clean_data():
    df = _make_series(spike_at=None)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    # Very few false positives expected in normal data
    assert results["severity"].isna().sum() >= len(results) * 0.94


def test_detects_spike():
    df = _make_series(spike_at=500, spike_magnitude=6.0)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    spike_row = results.iloc[500]
    assert spike_row["severity"] == "critical"
    assert 0.0 <= spike_row["anomaly_score"] <= 1.0


def test_score_normalized():
    df = _make_series(spike_at=500, spike_magnitude=4.0)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    scores = results["anomaly_score"].dropna()
    assert scores.min() >= 0.0
    assert scores.max() <= 1.0

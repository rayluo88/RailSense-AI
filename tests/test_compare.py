import numpy as np
import pandas as pd

from src.detection.compare import compare_detectors


def test_compare_returns_metrics():
    rng = np.random.default_rng(42)
    n = 576
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=n, freq="5min"),
        "value": rng.normal(35, 2, n),
    })
    is_anomaly = np.zeros(n, dtype=bool)
    is_anomaly[300] = True
    df["is_anomaly"] = is_anomaly
    df.loc[300, "value"] += 20

    metrics = compare_detectors(df)
    assert "stl" in metrics
    assert "prophet" in metrics
    for m in metrics.values():
        assert "precision" in m
        assert "recall" in m
        assert "f1" in m
        assert "time_seconds" in m

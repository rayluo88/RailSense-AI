import numpy as np
import pandas as pd


class ZScoreDetector:
    def __init__(self, window: int = 288, threshold_warn: float = 2.0, threshold_crit: float = 3.0):
        self.window = window
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        values = result["value"].values.astype(float)

        rolling_mean = pd.Series(values).rolling(self.window, min_periods=1).mean().values
        rolling_std = pd.Series(values).rolling(self.window, min_periods=1).std().values
        rolling_std = np.where(rolling_std == 0, 1e-10, rolling_std)

        z_scores = np.abs((values - rolling_mean) / rolling_std)

        # Normalize score to 0-1 using sigmoid-like mapping
        max_z = max(self.threshold_crit * 2, z_scores.max()) if len(z_scores) > 0 else 1
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "zscore"
        return result

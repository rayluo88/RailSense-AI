import logging

import numpy as np
import pandas as pd
from prophet import Prophet

# Suppress noisy Prophet/cmdstanpy logging
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


class ProphetDetector:
    """Anomaly detector using Facebook Prophet forecast-based residuals.

    Fits a Prophet model to capture trend and daily seasonality, then
    computes z-scores from the residuals (actual - predicted).  Points
    whose z-score exceeds configurable thresholds are flagged as
    warning or critical anomalies.
    """

    def __init__(self, threshold_warn: float = 2.0, threshold_crit: float = 3.0, interval_width: float = 0.95):
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit
        self.interval_width = interval_width

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        prophet_df = pd.DataFrame({"ds": df["timestamp"], "y": df["value"]})

        model = Prophet(
            interval_width=self.interval_width,
            daily_seasonality=True,
            weekly_seasonality=False,
            yearly_seasonality=False,
        )
        model.fit(prophet_df)
        forecast = model.predict(prophet_df)

        residuals = df["value"].values - forecast["yhat"].values
        resid_std = np.std(residuals)
        resid_std = max(resid_std, 1e-10)
        z_scores = np.abs(residuals / resid_std)

        max_z = max(self.threshold_crit * 2, z_scores.max())
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "prophet"
        return result

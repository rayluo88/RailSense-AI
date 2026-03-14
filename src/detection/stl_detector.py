import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


class STLDetector:
    """Anomaly detector using STL (Seasonal-Trend decomposition using LOESS).

    Decomposes the signal into trend + seasonal + residual, then flags
    data points whose residual z-score exceeds configurable thresholds.

    A two-pass approach is used: the first pass (non-robust) captures the
    raw residuals including any outliers, then MAD-based z-scores are
    computed so that a single extreme point does not inflate the scale
    estimate and mask itself.
    """

    def __init__(self, period: int = 288, threshold_warn: float = 2.0, threshold_crit: float = 3.0):
        self.period = period
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        series = pd.Series(result["value"].values, index=result["timestamp"])

        # seasonal_deg=0 forces a constant (mean) seasonal estimate per
        # time-of-day slot, preventing overfitting when few full cycles
        # are available (e.g. only 2 days of data with period=288).
        stl = STL(series, period=self.period, seasonal=7, seasonal_deg=0, robust=False)
        decomposition = stl.fit()
        residuals = decomposition.resid.values

        # Use MAD (median absolute deviation) for robust scale estimation
        # so a single large outlier doesn't inflate the std and mask itself
        median_resid = np.median(residuals)
        mad = np.median(np.abs(residuals - median_resid))
        # Convert MAD to std-equivalent (for normal distribution, std ≈ 1.4826 * MAD)
        resid_scale = max(1.4826 * mad, 1e-10)
        z_scores = np.abs((residuals - median_resid) / resid_scale)

        max_z = max(self.threshold_crit * 2, z_scores.max())
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "stl"
        return result

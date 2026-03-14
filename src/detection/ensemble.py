import numpy as np
import pandas as pd


class EnsembleScorer:
    def __init__(
        self,
        weights: list[float] | None = None,
        threshold_info: float = 0.4,
        threshold_warn: float = 0.5,
        threshold_crit: float = 0.8,
    ):
        self.weights = weights
        self.threshold_info = threshold_info
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def combine(self, results: list[pd.DataFrame]) -> pd.DataFrame:
        n = len(results)
        weights = self.weights or [1.0 / n] * n
        scores = np.stack([r["anomaly_score"].values for r in results])

        weighted_avg = np.average(scores, axis=0, weights=weights)

        # Agreement boost: if multiple methods flag the same point, boost score
        flagged = (scores >= 0.5).sum(axis=0)
        agreement_factor = 1.0 + 0.1 * (flagged - 1)
        ensemble_score = np.clip(weighted_avg * agreement_factor, 0.0, 1.0)

        severity = []
        for s in ensemble_score:
            if s >= self.threshold_crit:
                severity.append("critical")
            elif s >= self.threshold_warn:
                severity.append("warning")
            elif s >= self.threshold_info:
                severity.append("info")
            else:
                severity.append("info")

        return pd.DataFrame({
            "ensemble_score": ensemble_score,
            "ensemble_severity": severity,
            "methods_agreed": flagged,
        })

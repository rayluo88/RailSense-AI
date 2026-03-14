import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


SENSOR_COLS = ["vibration", "temperature", "door_cycle", "current_draw"]


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        X = result[SENSOR_COLS].values

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=200,
        )
        model.fit(X)

        raw_scores = model.decision_function(X)
        # decision_function: lower = more anomalous. Invert and normalize to 0-1.
        scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)

        severity = pd.array([None] * len(df), dtype=object)
        severity[scores >= 0.8] = "critical"
        severity[(scores >= 0.6) & (scores < 0.8)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "isolation_forest"
        return result

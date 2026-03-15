import pandas as pd

from src.detection.ensemble import EnsembleScorer
from src.detection.isolation_forest import IsolationForestDetector
from src.detection.prophet_detector import ProphetDetector
from src.detection.stl_detector import STLDetector
from src.detection.zscore import ZScoreDetector

DETECTOR_MAP = {
    "zscore": lambda: ZScoreDetector(),
    "isolation_forest": lambda: IsolationForestDetector(),
    "stl": lambda: STLDetector(),
    "prophet": lambda: ProphetDetector(),
}


class DetectionPipeline:
    def __init__(self, methods: list[str] | None = None):
        self.methods = methods or ["zscore", "stl", "isolation_forest"]
        self.scorer = EnsembleScorer()

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(self.methods) == 1:
            detector = DETECTOR_MAP[self.methods[0]]()
            return detector.detect(df)

        results = []
        for method_name in self.methods:
            if method_name == "isolation_forest":
                continue  # handled separately — needs multivariate input
            detector = DETECTOR_MAP[method_name]()
            results.append(detector.detect(df))

        if len(results) == 0:
            return df

        if len(results) == 1:
            return results[0]

        combined = self.scorer.combine(results)
        output = df.copy()
        output["ensemble_score"] = combined["ensemble_score"]
        output["ensemble_severity"] = combined["ensemble_severity"]
        output["methods_agreed"] = combined["methods_agreed"]
        return output

    def get_anomaly_events(self, df: pd.DataFrame) -> list[dict]:
        result = self.run(df)

        score_col = "ensemble_score" if "ensemble_score" in result.columns else "anomaly_score"
        severity_col = "ensemble_severity" if "ensemble_severity" in result.columns else "severity"

        events = []
        for _, row in result.iterrows():
            sev = row.get(severity_col)
            if sev in ("warning", "critical"):
                events.append({
                    "timestamp": row["timestamp"],
                    "train_id": row.get("train_id", ""),
                    "sensor_type": row.get("sensor_type", ""),
                    "anomaly_score": float(row[score_col]),
                    "severity": sev,
                    "value": float(row["value"]),
                    "line_id": row.get("line_id", ""),
                    "station_id": row.get("station_id", ""),
                    "detection_method": ",".join(self.methods),
                })
        return events

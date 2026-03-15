import time

import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

from src.detection.stl_detector import STLDetector
from src.detection.prophet_detector import ProphetDetector


def compare_detectors(df: pd.DataFrame) -> dict:
    ground_truth = df["is_anomaly"].values.astype(int)
    results = {}

    for name, detector in [("stl", STLDetector()), ("prophet", ProphetDetector())]:
        start = time.time()
        detected = detector.detect(df)
        elapsed = time.time() - start

        predicted = np.where(detected["severity"].isna(), 0, 1)

        results[name] = {
            "precision": float(precision_score(ground_truth, predicted, zero_division=0)),
            "recall": float(recall_score(ground_truth, predicted, zero_division=0)),
            "f1": float(f1_score(ground_truth, predicted, zero_division=0)),
            "time_seconds": round(elapsed, 2),
            "total_flagged": int(predicted.sum()),
            "true_anomalies": int(ground_truth.sum()),
        }

    return results

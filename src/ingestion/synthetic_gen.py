from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class AnomalyScenario:
    sensor_types: list[str]
    start_hour: int
    duration_hours: int
    magnitude: float = 3.0
    gradual: bool = False


SENSOR_BASELINES = {
    "vibration": {"mean": 0.3, "std": 0.05, "unit": "g"},
    "temperature": {"mean": 35.0, "std": 2.0, "unit": "\u00b0C"},
    "door_cycle": {"mean": 2500, "std": 100, "unit": "ms"},
    "current_draw": {"mean": 150, "std": 15, "unit": "A"},
}

# Peak hour multipliers -- higher load during rush hours
PEAK_HOURS = {7, 8, 9, 17, 18, 19}
PEAK_MULTIPLIER = {
    "vibration": 1.15,
    "temperature": 1.20,
    "door_cycle": 1.05,
    "current_draw": 1.25,
}


class SyntheticGenerator:
    def __init__(self, seed: int = 42, interval_minutes: int = 5):
        self.rng = np.random.default_rng(seed)
        self.interval_minutes = interval_minutes

    def generate(
        self,
        train_id: str,
        hours: int,
        line_id: str = "NSL",
        station_id: str = "NS1",
        anomalies: list[AnomalyScenario] | None = None,
    ) -> pd.DataFrame:
        anomalies = anomalies or []
        n_points = (hours * 60) // self.interval_minutes
        start = pd.Timestamp("2026-03-01")
        timestamps = pd.date_range(start, periods=n_points, freq=f"{self.interval_minutes}min")

        rows = []
        for sensor_type, baseline in SENSOR_BASELINES.items():
            values = self.rng.normal(baseline["mean"], baseline["std"], n_points)

            # Apply daily ridership pattern
            for i, ts in enumerate(timestamps):
                if ts.hour in PEAK_HOURS:
                    values[i] *= PEAK_MULTIPLIER[sensor_type]

            # Mark anomalies
            is_anomaly = np.zeros(n_points, dtype=bool)

            for scenario in anomalies:
                if sensor_type not in scenario.sensor_types:
                    continue
                start_idx = (scenario.start_hour * 60) // self.interval_minutes
                end_idx = start_idx + (scenario.duration_hours * 60) // self.interval_minutes
                end_idx = min(end_idx, n_points)

                for i in range(start_idx, end_idx):
                    if scenario.gradual:
                        progress = (i - start_idx) / max(end_idx - start_idx, 1)
                        values[i] += baseline["std"] * scenario.magnitude * progress
                    else:
                        values[i] += baseline["std"] * scenario.magnitude
                    is_anomaly[i] = True

            for i in range(n_points):
                rows.append({
                    "timestamp": timestamps[i],
                    "train_id": train_id,
                    "sensor_type": sensor_type,
                    "value": float(values[i]),
                    "line_id": line_id,
                    "station_id": station_id,
                    "is_anomaly": bool(is_anomaly[i]),
                })

        return pd.DataFrame(rows)

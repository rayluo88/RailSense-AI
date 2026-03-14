from typing import Protocol

import pandas as pd


class Detector(Protocol):
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Input: DataFrame with 'timestamp' and 'value' columns.
        Output: Same DataFrame with added 'anomaly_score' and 'severity' columns.
        """
        ...

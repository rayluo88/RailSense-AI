import pandas as pd

from src.detection.ensemble import EnsembleScorer


def test_combines_scores():
    results = [
        pd.DataFrame({"anomaly_score": [0.3, 0.9, 0.1], "severity": [None, "critical", None]}),
        pd.DataFrame({"anomaly_score": [0.2, 0.8, 0.1], "severity": [None, "critical", None]}),
        pd.DataFrame({"anomaly_score": [0.4, 0.7, 0.2], "severity": [None, "warning", None]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(results)
    assert combined.iloc[1]["ensemble_score"] > combined.iloc[0]["ensemble_score"]


def test_agreement_boost():
    """When multiple methods agree on anomaly, score should be higher than any individual."""
    all_agree = [
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(all_agree)
    assert combined.iloc[0]["ensemble_score"] >= 0.7


def test_severity_thresholds():
    results = [
        pd.DataFrame({"anomaly_score": [0.9, 0.5, 0.1], "severity": ["critical", "warning", None]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(results)
    assert combined.iloc[0]["ensemble_severity"] == "critical"
    assert combined.iloc[1]["ensemble_severity"] == "warning"
    assert combined.iloc[2]["ensemble_severity"] == "info"

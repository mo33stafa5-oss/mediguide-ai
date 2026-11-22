import json
from pathlib import Path

import pytest

from ml.features import FEATURES
from backend.app.services import ml_service

ART = Path(__file__).resolve().parents[2] / "ml"
SAMPLE = dict(age=63, sex=1, cp=1, trestbps=145, chol=233, fbs=1, restecg=2, thalach=150, exang=0, oldpeak=2.3, slope=3, ca=0, thal=6)


def test_artifacts_exist():
    assert (ART / "artifacts/heart_model.joblib").exists() and (ART / "reports/evaluation.json").exists()


def test_predict_returns_probability_and_version():
    r = ml_service.predict(SAMPLE)
    assert 0 <= r["score"] <= 1 and r["prediction"] in (0, 1) and r["model_version"].startswith("mediguide-heart")


def test_report_matches_dataset_and_no_leakage_design():
    m = json.loads((ART / "reports/evaluation.json").read_text())
    d = m["dataset"]
    assert d["rows"] == 303 and d["train_rows"] + d["test_rows"] == 303 and d["missing_values"] == {"ca": 4, "thal": 2}
    assert set(m["results"]) == {"Logistic Regression", "Random Forest", "Decision Tree", "Support Vector Machine"}
    assert "training split" in m["selection_rule"]  # selection NOT on test set
    for r in m["results"].values():
        c = r["confusion_matrix"]
        assert c["tn"] + c["fp"] + c["fn"] + c["tp"] == d["test_rows"]


def test_dataset_file_hash_matches_report():
    import hashlib
    m = json.loads((ART / "reports/evaluation.json").read_text())
    assert hashlib.sha256((ART / "data/processed.cleveland.data").read_bytes()).hexdigest() == m["dataset"]["file_sha256"]


def test_model_handles_missing_ca_thal_like_training():
    import pandas as pd
    df = pd.DataFrame([{**SAMPLE, "ca": None, "thal": None}])[FEATURES]
    assert ml_service.load_model().predict_proba(df).shape == (1, 2)

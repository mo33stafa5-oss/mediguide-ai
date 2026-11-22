"""Inference only. The model is trained offline by `python -m ml.train` and loaded once per process."""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from ml.features import FEATURES

ART = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


@lru_cache
def load_model():
    return joblib.load(ART / "heart_model.joblib")


@lru_cache
def model_meta() -> dict:
    return json.loads((ART / "model_meta.json").read_text())


def predict(features: dict) -> dict:
    meta = model_meta()
    df = pd.DataFrame([{k: features[k] for k in FEATURES}])
    proba = float(load_model().predict_proba(df)[0, 1])
    return {"prediction": int(proba >= 0.5), "score": round(proba, 4), "model_version": meta["model_version"],
            "model_name": meta["selected_model"]}

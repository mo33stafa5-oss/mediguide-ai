"""Train and compare 4 scikit-learn models on the UCI Cleveland heart-disease data.

Run:  python -m ml.train
Outputs (real, regenerated on every run): ml/artifacts/*.joblib, ml/reports/*.json|md|png
Never executed at API request time or at deployment time.
"""
from __future__ import annotations
import json, hashlib, platform
from datetime import datetime, timezone
from pathlib import Path

import warnings; warnings.filterwarnings("ignore", category=FutureWarning)
import joblib, numpy as np, pandas as pd, sklearn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix, roc_curve)

from ml.features import COLUMNS, NUMERIC, CATEGORICAL, BINARY, FEATURES, MODEL_VERSION

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "processed.cleveland.data"
ART, REP = ROOT / "artifacts", ROOT / "reports"
SEED = 42


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA, header=None, names=COLUMNS, na_values="?")
    df["target"] = (df["num"] > 0).astype(int)
    return df


def preprocessor() -> ColumnTransformer:
    num = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    cat = Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                    ("oh", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("num", num, NUMERIC), ("cat", cat, CATEGORICAL), ("bin", "passthrough", BINARY)])


def candidates():
    return {
        "Logistic Regression": (LogisticRegression(max_iter=2000, random_state=SEED),
                                {"clf__C": [0.01, 0.1, 1, 10]}),
        "Random Forest": (RandomForestClassifier(random_state=SEED),
                          {"clf__n_estimators": [100, 300], "clf__max_depth": [3, 5, None],
                           "clf__min_samples_leaf": [1, 3]}),
        "Decision Tree": (DecisionTreeClassifier(random_state=SEED),
                          {"clf__max_depth": [2, 3, 4, 5, None], "clf__min_samples_leaf": [1, 5, 10]}),
        "Support Vector Machine": (SVC(probability=True, random_state=SEED),
                                   {"clf__C": [0.1, 1, 10], "clf__kernel": ["linear", "rbf"],
                                    "clf__gamma": ["scale", 0.01]}),
    }


def main() -> dict:
    ART.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
    df = load()
    X, y = df[FEATURES], df["target"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)

    results, fitted, curves = {}, {}, {}
    for name, (clf, grid) in candidates().items():
        pipe = Pipeline([("prep", preprocessor()), ("clf", clf)])
        # Hyper-parameters are tuned by CV on the TRAINING split only (no test leakage).
        gs = GridSearchCV(pipe, grid, cv=cv, scoring="roc_auc", n_jobs=1).fit(X_tr, y_tr)
        best = gs.best_estimator_
        pred, proba = best.predict(X_te), best.predict_proba(X_te)[:, 1]
        tn, fp, fn, tp = confusion_matrix(y_te, pred).ravel()
        fpr, tpr, _ = roc_curve(y_te, proba)
        curves[name] = (fpr, tpr)
        results[name] = {
            "best_params": {k.replace("clf__", ""): v for k, v in gs.best_params_.items()},
            "cv_roc_auc_mean_train_only": round(float(gs.best_score_), 4),
            "test": {"accuracy": round(accuracy_score(y_te, pred), 4),
                     "precision": round(precision_score(y_te, pred), 4),
                     "recall": round(recall_score(y_te, pred), 4),
                     "f1": round(f1_score(y_te, pred), 4),
                     "roc_auc": round(roc_auc_score(y_te, proba), 4)},
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        }
        fitted[name] = best

    # Model selection uses CV score from the training split only (NOT the test set).
    selected = max(results, key=lambda n: results[n]["cv_roc_auc_mean_train_only"])
    final = fitted[selected]
    sha = hashlib.sha256(DATA.read_bytes()).hexdigest()
    meta = {
        "model_version": MODEL_VERSION,
        "selected_model": selected,
        "selection_rule": "highest 5-fold CV ROC-AUC on the training split",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {"name": "UCI Heart Disease (Cleveland)", "file_sha256": sha,
                    "rows": int(len(df)), "positive": int(y.sum()), "negative": int((1 - y).sum()),
                    "missing_values": {c: int(v) for c, v in df[FEATURES].isna().sum().items() if v},
                    "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
                    "split": "80/20 stratified, random_state=42"},
        "features": FEATURES,
        "versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__},
        "results": results,
        "disclaimer": "Educational/research model on 303 patients from one site; not clinically validated.",
    }
    joblib.dump(final, ART / "heart_model.joblib", compress=3)
    (ART / "model_meta.json").write_text(json.dumps(meta, indent=2))
    (REP / "evaluation.json").write_text(json.dumps(meta, indent=2))

    # Charts from the real results
    fig, ax = plt.subplots(figsize=(6, 5))
    for n, (f, t) in curves.items():
        ax.plot(f, t, label=f"{n} (AUC={results[n]['test']['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1); ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves (held-out test set)"); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(REP / "roc_curves.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(1, 4, figsize=(14, 3.4))
    for a, (n, r) in zip(ax, results.items()):
        c = r["confusion_matrix"]; m = np.array([[c["tn"], c["fp"]], [c["fn"], c["tp"]]])
        a.imshow(m, cmap="Blues")
        for (i, j), v in np.ndenumerate(m): a.text(j, i, v, ha="center", va="center")
        a.set_xticks([0, 1], ["Pred 0", "Pred 1"]); a.set_yticks([0, 1], ["True 0", "True 1"]); a.set_title(n, fontsize=9)
    fig.tight_layout(); fig.savefig(REP / "confusion_matrices.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4)); names = list(results); w = 0.16
    for k, m in enumerate(["accuracy", "precision", "recall", "f1", "roc_auc"]):
        ax.bar(np.arange(4) + k * w, [results[n]["test"][m] for n in names], w, label=m)
    ax.set_xticks(np.arange(4) + 2 * w, [n.replace(" ", "\n") for n in names], fontsize=8); ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7, ncol=5); ax.set_title("Test metrics by model"); fig.tight_layout()
    fig.savefig(REP / "model_comparison.png", dpi=150); plt.close(fig)

    md = [f"# Evaluation report ({MODEL_VERSION})", "",
          f"Generated {meta['trained_at_utc']} by `python -m ml.train`. Rows: {len(df)} "
          f"(train {len(X_tr)}, test {len(X_te)}). Selected: **{selected}** ({meta['selection_rule']}).", "",
          "| Model | Acc | Prec | Rec | F1 | ROC-AUC | CV AUC (train) | TN | FP | FN | TP |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in results.items():
        t, c = r["test"], r["confusion_matrix"]
        md.append(f"| {n} | {t['accuracy']} | {t['precision']} | {t['recall']} | {t['f1']} | {t['roc_auc']} | "
                  f"{r['cv_roc_auc_mean_train_only']} | {c['tn']} | {c['fp']} | {c['fn']} | {c['tp']} |")
    md += ["", "Test set has only 61 patients: differences between models are within statistical noise.", "",
           "![ROC](roc_curves.png)", "![CM](confusion_matrices.png)", "![Comparison](model_comparison.png)"]
    (REP / "evaluation.md").write_text("\n".join(md))
    return meta


if __name__ == "__main__":
    m = main()
    print(json.dumps({k: m[k] for k in ("selected_model", "dataset")}, indent=2))
    for n, r in m["results"].items(): print(n, r["test"], r["confusion_matrix"], r["best_params"])

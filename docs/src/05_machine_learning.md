# Part 5 — Machine Learning

## 25. Machine Learning Theory and Implementation
**Supervised binary classification.** Given 13 patient features *x*, learn *f(x) → {0,1}* where 1 = heart disease present (UCI `num > 0`). Learning from labelled examples is *supervised*; predicting a category is *classification*.

> **بالعربي:** نعطي الكمبيوتر بيانات 303 مريضًا مع النتيجة (مريض/سليم) ليتعلم النمط، ثم نختبره على مرضى لم يرهم قبل ذلك.

**Why Python and scikit-learn.** Python has the dominant data-science ecosystem; scikit-learn gives a uniform `fit/predict` API, `Pipeline`, cross-validation and all four required algorithms with no GPU. The dataset is tiny and tabular, where classical models are appropriate (deep learning would overfit 303 rows).

**Pipeline (`ml/train.py`, run with `python -m ml.train`)**
1. Load `ml/data/processed.cleveland.data` (`?` → NaN). 2. Inspect (counts, missing). 3. Clean/binarise target. 4. **Impute** (median for numeric, most-frequent for categorical). 5. **Encode** categorical `cp, restecg, slope, thal` with one-hot (`handle_unknown="ignore"`). 6. **Scale** numeric features (StandardScaler) — important for LR and SVM, harmless for trees. 7. Stratified 80/20 split (seed 42). 8. Train four models. 9. **Tune with 5-fold stratified `GridSearchCV` on the training split only** (all preprocessing lives inside the pipeline so imputers/scalers are fitted per fold: no leakage). 10. Evaluate each tuned model **once** on the held-out test split. 11. **Select the model by cross-validation score, not test score**, so the test set stays unbiased. 12. Save `heart_model.joblib` (pipeline) and `model_meta.json`; write `evaluation.json/md` and three PNG charts.

Training never runs inside the API or at deployment; the committed artifact is loaded read-only.

## 26. Dataset Documentation
- **Source:** Janosi, Steinbrunn, Pfisterer, Detrano (1988), *Heart Disease*, UCI Machine Learning Repository, DOI 10.24432/C52P4X; subset: Cleveland Clinic (`processed.cleveland.data`).
- **License:** CC BY 4.0 (as published by UCI) — attribution required (given here).
- **Provenance caveat:** the UCI host was blocked in the build sandbox. The file was fetched from the public GitHub mirror `nyuvis/datasets`; its SHA-256 `a74b7efa…427c8` is identical to three other independent GitHub copies. Authors should re-download from UCI and confirm the hash (`ml/data/SOURCE.txt`).
- **Rows/columns:** 303 × 14 (13 features + `num`). Target distribution after binarising: 139 disease, 164 no disease.
- **Missing values:** `ca` ×4, `thal` ×2 (marked `?`).
- **Features:** see table.

| Feature | Meaning | Type |
|---|---|---|
| age | years | numeric |
| sex | 1 male, 0 female | binary |
| cp | chest-pain type 1–4 | categorical |
| trestbps | resting BP (mm Hg) | numeric |
| chol | serum cholesterol (mg/dl) | numeric |
| fbs | fasting sugar > 120 mg/dl | binary |
| restecg | resting ECG 0–2 | categorical |
| thalach | max heart rate achieved | numeric |
| exang | exercise-induced angina | binary |
| oldpeak | ST depression (exercise vs rest) | numeric |
| slope | ST slope 1–3 | categorical |
| ca | major vessels coloured (0–3) | numeric |
| thal | 3 normal, 6 fixed, 7 reversible defect | categorical |

- **Limitations:** 303 patients, one hospital, collected in the 1980s, mostly male, no external validation, label is "angiographic disease present" not future risk. Results may not generalise to Egyptian patients today.

## 27. ML Algorithms Explanation
**Logistic Regression.** Models `P(y=1|x) = σ(wᵀx + b)`, `σ(z) = 1/(1+e^{−z})`; minimises log-loss `−Σ[y log p + (1−y) log(1−p)]` with L2 penalty; hyper-parameter `C` = inverse regularisation strength. Linear, interpretable, strong baseline on small data.

**Decision Tree.** Recursively splits on the feature/threshold that most reduces impurity, `Gini = 1 − Σ pₖ²`. Easy to explain, prone to overfitting → tuned with `max_depth`, `min_samples_leaf`.

**Random Forest.** Many trees trained on bootstrap samples with random feature subsets; prediction = average vote. Reduces variance versus a single tree. Tuned: `n_estimators`, `max_depth`, `min_samples_leaf`.

**Support Vector Machine.** Finds the maximum-margin separating boundary; with the RBF kernel `K(x,x′) = exp(−γ‖x−x′‖²)` it separates non-linear patterns. Tuned: `C`, `kernel`, `gamma`. `probability=True` calibrates scores via Platt scaling (scikit-learn 1.9 deprecates this flag; a `FutureWarning` is suppressed in the training script and the flag is a known to-do).

## 28. Model Evaluation and Results
**Metrics.** With TP/FP/TN/FN from the confusion matrix: Accuracy = (TP+TN)/N; Precision = TP/(TP+FP); Recall (sensitivity) = TP/(TP+FN); F1 = 2PR/(P+R); ROC-AUC = area under TPR-vs-FPR curve over all thresholds (probability that a random positive scores above a random negative). In a screening context **recall** (missing a sick patient) usually matters more than precision.

### Actual results — executed by `python -m ml.train` (identical on two separate runs)
{{ML_TABLE}}

Charts: `ml/reports/roc_curves.png`, `confusion_matrices.png`, `model_comparison.png`; full machine-readable report `ml/reports/evaluation.json`.

### Honest interpretation
- The test set has only **61** patients: one patient changes accuracy by ≈1.6 points, so differences between models are within noise. The SVM has the highest *test* accuracy and F1, but the *selection rule* (CV on the training split) chose **Logistic Regression**; we report this rather than switching to the "best looking" test number, which would leak the test set into model choice.
- All four models reach recall 0.93 (SVM/LR/RF) or 0.86 (tree); AUC ≈ 0.95–0.96 for the three stronger models. These are **single-split, single-site estimates**, not clinical performance. No confidence intervals, calibration study, fairness analysis or external validation were done (**Planned / Future Work**).
- The API returns the score as "model score", with model version, limitations and disclaimer; it is never called a diagnosis or a validated personal probability.

### Serving
`POST /api/predict` → Pydantic range validation → `ml_service.predict` (cached joblib) → row stored in `heart_risk_assessments` (inputs, score, model version). `GET /api/model-info` returns the metadata above. Scores from different model versions are flagged as not comparable.

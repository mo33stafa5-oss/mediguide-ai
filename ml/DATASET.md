# Dataset: UCI Heart Disease (Cleveland subset)

- Original source: Janosi, A., Steinbrunn, W., Pfisterer, M., Detrano, R. (1988). *Heart Disease*. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X
- License: Creative Commons Attribution 4.0 (CC BY 4.0), as stated by the UCI repository.
- File used: `processed.cleveland.data` (303 rows, 14 columns, no header). The UCI host is not reachable from the build sandbox; the file was fetched from a public GitHub mirror (nyuvis/datasets) and its SHA-256 was identical to three other independent mirrors (see `ml/data/SOURCE.txt`). Verify against UCI yourself before publishing results.
- Target `num`: 0 = no disease, 1-4 = disease present. We binarise: `target = (num > 0)`.
- Missing values: marked `?` in `ca` (4 rows) and `thal` (2 rows).
- Limitations: 303 patients, one hospital (Cleveland Clinic, collected in the 1980s), small sample, mostly male, no external validation. Results are for education/research only.

| Column | Meaning | Type |
|---|---|---|
| age | Age in years | numeric |
| sex | 1 = male, 0 = female | binary |
| cp | Chest pain type (1 typical angina, 2 atypical angina, 3 non-anginal, 4 asymptomatic) | categorical |
| trestbps | Resting blood pressure (mm Hg) | numeric |
| chol | Serum cholesterol (mg/dl) | numeric |
| fbs | Fasting blood sugar > 120 mg/dl (1 = true) | binary |
| restecg | Resting ECG (0 normal, 1 ST-T abnormality, 2 LV hypertrophy) | categorical |
| thalach | Maximum heart rate achieved | numeric |
| exang | Exercise-induced angina (1 = yes) | binary |
| oldpeak | ST depression induced by exercise relative to rest | numeric |
| slope | Slope of peak exercise ST segment (1 up, 2 flat, 3 down) | categorical |
| ca | Number of major vessels (0-3) coloured by fluoroscopy | numeric |
| thal | 3 normal, 6 fixed defect, 7 reversible defect | categorical |

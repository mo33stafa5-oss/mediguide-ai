# Part 6 — OCR, Medical Documents and Prescription Safety

## 29. OCR and Computer Vision
**Tools actually used:** Pillow (decode/validate), OpenCV (`opencv-python-headless`) for pre-processing, Tesseract through `pytesseract` for recognition (languages `eng+ara` when installed), `pypdf` for digital PDFs, `pdftoppm` (poppler) to rasterise scanned PDFs. PaddleOCR was **not** used.

**Pre-processing (`ocr/engine.py::preprocess`).** Decode as grayscale → upscale so the long side ≥ 1600 px (Tesseract is most accurate near 300 DPI) → `fastNlMeansDenoising` → Gaussian **adaptive threshold** (local binarisation copes with uneven lighting).

**Recognition.** `image_to_data` returns each word with a 0–100 confidence. We keep text per line, compute the mean, list words below 60, and raise a warning if the mean is below 60. In our synthetic lab test the mean confidence was ≈ 94.6/100 — *clean, computer-rendered text; real photographs will score lower.*

**Uncertainty handling.** (1) low-confidence warnings; (2) plausibility ranges for ECG numbers; (3) lab values compared **only** with a range printed on the same line; otherwise status `unknown`; (4) fuzzy drug-name matches below 95 % flagged; (5) unrecognised names are left `null` rather than guessed; (6) every report is labelled "OCR output, not verified".

**Safety/validation (`ocr/validate.py`).** Type is decided by *magic bytes*, not the client MIME; extension must match; ≤ 20 MB; Pillow must decode the image; pixel limit 40 MP (decompression-bomb guard); minimum 100×100; PDFs must be unencrypted, ≤ 20 pages; filenames sanitised against path traversal. DICOM is rejected (no pipeline).

**Where it runs.** Tesseract is a system binary, so OCR runs in the Docker worker (`Dockerfile.ocr`). The API calls `POST /internal/ocr` with `X-Worker-Token` (constant-time comparison) when Tesseract is not local. Digital-text PDFs need no worker.

> **بالعربي:** OCR يقرأ الحروف من الصورة. لا نثق به 100%: نعرض نسبة الثقة، ولا نخمّن أي قيمة غير واضحة، ونطلب من المستخدم مراجعتها.

## 30. Medical Document Processing
| Type | Bucket | Implemented workflow | Explicitly NOT done |
|---|---|---|---|
| Lab report | `lab-reports` | OCR → lines `name value unit (lo - hi)` → status low/high/within_range/unknown; report date | Reference ranges from textbooks; trend comparison across labs |
| ECG | `ecg-reports` | OCR of printed HR, PR, QRS, QT, QTc with plain-language meaning; plausibility checks | Waveform analysis, rhythm diagnosis from photos |
| X-ray | `xray-images` | Validation, private storage, technical metadata (size, mode, mean intensity) | Any finding/diagnosis; Gemini image descriptions (deliberately avoided); research classifier **Planned** |
| Prescription | `prescriptions` | OCR → medication candidates with dose/frequency/duration → human confirmation | Handwriting recognition |
| General | `general-documents` | Text extraction only | – |

**Type detection.** `detect_document_type` scores keyword families (ECG: qrs, qtc, "sinus rhythm"…; lab: "reference range", cholesterol…; prescription: tab, mg, rx…). If the detected type differs from the chosen type a warning is added. It requires ≥ 2 keyword hits; otherwise `None`.

**Historical comparison.** Each report stores its own units and ranges, but automatic cross-report comparison is **Planned / Future Work**; the dashboard timeline only orders events. The rule "compare only when comparable" is satisfied by not comparing.

## 31. Prescription Safety (Prescription & Medication Safety Review)
Checks in `services/drugs.py::review`:
| Check | Logic | Severity |
|---|---|---|
| Duplicate | same normalised name appears > 1 time | warning |
| Missing dosage / frequency | recognised drug with no dose / frequency | warning / info |
| Uncertain OCR | name matched approximately or low document confidence | warning |
| Unrecognised name | not in the lexicon → never guessed | warning |
| Allergy | recorded allergy substring-matches a drug name (either direction) | **critical** |
| Interaction class | curated rules in `backend/data/interactions.json` (warfarin/anticoagulants + antiplatelets/NSAIDs; PDE5 inhibitors + nitrates; ACEi/ARB + potassium-sparing; simvastatin + amiodarone/CCBs; clopidogrel + omeprazole; digoxin + amiodarone/verapamil) with a source pointer to the FDA label on DailyMed | major / moderate / contraindicated |
| Drug information | live DailyMed `spls.json` lookup → label titles + links; if unreachable, status `unavailable` | – |

**Limits stated to the user:** the interaction list is a *small curated starter set*, `needs_reviewer_approval=true`, **not exhaustive**; no warning ≠ safe; allergy check requires a recorded allergy; the substring allergy match does not know drug classes (a penicillin allergy will not flag amoxicillin). NLM retired the RxNav interaction API in 2024, so no live interaction service is used. The DailyMed call could not be tested against the real service from the sandbox (host blocked) — the tests verify the honest "unavailable" path only.

**Never:** prescribe, stop, replace or change a dose, or call a prescription safe. Every result ends with the pharmacist/doctor notice (EN + AR). Saving requires the user to confirm the OCR output; saved medications have `verified=false`.

# Part 9 — Limitations, Future Work, Glossary, References

## 37. System Limitations
1. **Educational/research only.** Not clinically validated; no regulatory approval.
2. **Gemini chat/RAG unverified against the real service** (no key); the approved knowledge base is **empty** until an administrator adds real sources.
3. **ML:** 303 patients, single site, 1980s data, single split, no calibration/fairness/external validation; differences between algorithms are statistically insignificant.
4. **X-ray and ECG waveform analysis are not implemented**; only validation/metadata and printed-number OCR.
5. **OCR:** Tesseract on printed text only; no handwriting; accuracy on phone photos unmeasured; Arabic OCR untested; parsers are regex-based and fit simple line layouts (multi-column lab tables may fail).
6. **Medication safety:** tiny curated interaction list, name-substring allergy matching, DailyMed lookup untested live; no dose-range checks.
7. **Security gaps:** no CSP, per-instance rate limit, no MFA, no antivirus scanning, retention policy not enforced, no pen-test.
8. **Not deployed**; Vercel behaviour unverified; the Dockerised OCR worker was not run as a container (Docker daemon was available for Supabase, but the image was not built here).
9. **UI:** the hand-written shadcn-style components, no visual regression tests, English/Arabic strings written by the developer (not professionally reviewed medical translation).
10. Features in the reference image that are **not** built: appointments, hospital dashboards/white-label, usage analytics for hospitals.

## 38. Future Improvements
Run the app against real Gemini and evaluate answer quality (e.g., a reviewed question set); ingest WHO/AHA/CDC/MedlinePlus pages with reviewer workflow and automatic review-date expiry; chest X-ray research classifier on a public dataset with independent evaluation; ECG waveform classifier (e.g., on PhysioNet datasets) with proper validation; better OCR (PaddleOCR, layout analysis), Arabic benchmarks; a licensed drug-interaction data source and drug-class allergy mapping; cross-report lab trend comparison with unit conversion; MFA, CSP, global rate limiting (Redis), upload virus scanning, retention job, DB-level audit triggers; model calibration, confidence intervals, fairness analysis, external validation and clinician review; accessibility audit; clinical safety case and regulatory pathway (EDA) before real use.

## 39. Technical Glossary (English — العربية)
| Term | Meaning |
|---|---|
| API | Interface through which programs talk (واجهة برمجية) |
| ASGI | Python async web-server standard used by FastAPI |
| AUC / ROC | Area under / curve of true-positive vs false-positive rate (مساحة تحت المنحنى) |
| Chunking | Splitting long text into pieces for embedding (تقطيع النص) |
| Confusion matrix | Table of TP/FP/TN/FN (مصفوفة الارتباك) |
| Cosine similarity | Angle-based similarity of two vectors (تشابه جيب التمام) |
| Cross-validation | Repeated train/validate splits inside the training data (التحقق المتقاطع) |
| Data leakage | Test information influencing training/model choice (تسرب البيانات) |
| Embedding | Numeric vector capturing meaning of text (تضمين) |
| Endpoint | A URL + method of the API (نقطة نهاية) |
| Feature / Target | Input variable / value to predict (خاصية / الهدف) |
| Gemini | Google's generative AI model family (جيميناي) |
| Hallucination | Confident but false model output (هلوسة) |
| HNSW | Graph index for fast vector search |
| Hyper-parameter | Setting chosen before training (معامل ضبط) |
| JWT | Signed login token (رمز الدخول) |
| MIME / magic bytes | File type label / real signature bytes of the file |
| OCR | Optical character recognition (التعرف الضوئي على الحروف) |
| One-hot encoding | Category → binary columns (ترميز ثنائي) |
| Overfitting | Model memorises training data (فرط التخصيص) |
| pgvector | PostgreSQL extension for vectors |
| Pipeline | Chain of preprocessing + model in one object (خط المعالجة) |
| RAG | Retrieval-Augmented Generation (توليد معزز بالاسترجاع) |
| Recall / Precision | Share of sick found / share of alarms correct (الاستدعاء / الدقة) |
| RLS | Row Level Security: database rules per row (أمان مستوى الصف) |
| Service role | Powerful server-only database key |
| Signed URL | Temporary link to a private file (رابط موقّع) |
| SSE | Server-Sent Events, one-way streaming (بث الأحداث) |
| Stratified split | Split keeping class proportions (تقسيم طبقي) |
| Supabase | Hosted Postgres + Auth + Storage platform |
| Tesseract | Open-source OCR engine |
| Zod / Pydantic | Validation libraries (TypeScript / Python) |

## 40. References
1. Janosi A., Steinbrunn W., Pfisterer M., Detrano R. (1988). *Heart Disease*. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X (CC BY 4.0).
2. Detrano R. et al. (1989). International application of a new probability algorithm for the diagnosis of coronary artery disease. *Am J Cardiol* 64:304–310.
3. Pedregosa F. et al. (2011). Scikit-learn: Machine Learning in Python. *JMLR* 12:2825–2830.
4. Lewis P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*.
5. Smith R. (2007). An Overview of the Tesseract OCR Engine. *ICDAR*.
6. World Health Organization — Cardiovascular diseases fact sheet. https://www.who.int/health-topics/cardiovascular-diseases
7. Supabase documentation (Auth, Row Level Security, Storage, pgvector). https://supabase.com/docs
8. Next.js 16 documentation (bundled in `node_modules/next/dist/docs`). https://nextjs.org/docs
9. FastAPI documentation. https://fastapi.tiangolo.com
10. Vercel documentation (Python runtime, Next.js). https://vercel.com/docs
11. Google Gemini API documentation. https://ai.google.dev/gemini-api/docs
12. U.S. National Library of Medicine — DailyMed web services. https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
13. Egypt Law No. 151 of 2020 on the Protection of Personal Data.
14. Hastie T., Tibshirani R., Friedman J. (2009). *The Elements of Statistical Learning*, 2nd ed. Springer.
*Items 6–13 are the organisations' public documentation as I know it; URLs were not fetched during this project (the sandbox blocked most external hosts) and should be checked before citing in a formal submission.*

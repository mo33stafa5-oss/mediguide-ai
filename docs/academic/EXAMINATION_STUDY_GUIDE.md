# MediGuide AI — Examination Study Guide

> Study this file last, after skimming the other documents. Every answer is based on what is **actually implemented** in this repository. Labels: **[Implemented]**, **[Partial]**, **[Planned]**. When unsure in the viva, say what is real and what is future work — honesty scores better than bluffing.

## Part A — The project in plain words

### A1. Complete project explanation
MediGuide AI is a website for **heart-health education**. A patient creates an account and gets a private workspace. Inside it they can (1) chat with an AI that explains heart topics and cites approved sources, (2) fill a form and get a score from a machine-learning model trained on a public heart-disease dataset, (3) upload lab reports, ECGs, X-rays and prescriptions, (4) have printed numbers read by OCR, and (5) check a prescription for duplicates, missing doses, allergy matches and known interaction classes. Every result says it is educational and not a diagnosis. Emergency words trigger an immediate "call 123" warning.

> **بالعربي:** موقع تعليمي لصحة القلب: شات ذكي، حاسبة خطر بنموذج تعلم آلة، رفع التحاليل/الروشتة وقراءتها بـ OCR، ومراجعة أمان الأدوية. كله "للتثقيف" وليس تشخيصًا.

### A2. How the system works from beginning to end
1. User opens `/` (Arabic RTL by default) → registers → Supabase sends a verification email → user confirms → logs in.
2. `proxy.ts` refreshes the session cookie and blocks `/app/*` if not logged in; the app layout loads the profile (role/status).
3. The browser reads its own rows straight from Supabase (RLS filters them). Anything with logic calls FastAPI at `/api/*` with the access token.
4. FastAPI verifies the token with Supabase Auth, loads role/status, validates input with Pydantic, runs the module (ML, chat, OCR…), and writes results with the **user's token** so RLS still applies.
5. Gemini is called only from the server. Files go to private Supabase Storage; the browser views them via 120-second signed links.

### A3. How to explain every major module
| Module | One-sentence explanation |
|---|---|
| Auth | Supabase handles users/passwords/emails; a trigger creates the profile; `proxy.ts` and the API enforce access |
| Database | PostgreSQL tables per feature; **RLS** makes each patient see only their rows |
| Chat | Question → emergency regex → retrieve approved sources (pgvector) → Gemini streams an answer with citations |
| RAG | "Open-book exam" for the AI: fetch approved text first, answer from it |
| ML | scikit-learn pipeline trained offline on UCI Cleveland; API only loads and predicts |
| Risk form | 13 validated fields → model score + limitations + disclaimer |
| Documents | Validate (magic bytes) → private storage → OCR/parse → "needs review" report |
| OCR | OpenCV cleans the image, Tesseract reads it with per-word confidence |
| Prescription safety | Rules over confirmed medications + DailyMed links; never says "safe" |
| Admin | Users/roles, knowledge approval, health, evaluation, audit |

### A4. Why each technology was selected
| Technology | Reason |
|---|---|
| **Python** | Best ecosystem for ML/OCR/data; one language for model training and the API; readable for an academic project |
| **scikit-learn** | Standard, uniform API (`fit/predict`, `Pipeline`, `GridSearchCV`); ideal for small tabular data; no GPU; small saved model |
| **FastAPI** | Type-validated requests, auto OpenAPI docs, streaming, runs on Vercel |
| **Pydantic** | Rejects invalid medical inputs automatically |
| **Next.js (App Router)** | SSR for first-paint RTL, route protection (`proxy.ts`), Vercel-native |
| **TypeScript** | Catches errors at build time; both language dictionaries must have the same keys |
| **Tailwind + shadcn-style components** | Fast consistent design system with logical RTL properties |
| **Supabase** | Postgres + Auth + Storage + pgvector in one managed service; RLS gives database-level security |
| **pgvector** | Vector search inside the same database as the data, so approval status can be filtered in SQL |
| **Gemini** | Multilingual (Arabic), streaming, embeddings from the same vendor |
| **Tesseract + OpenCV** | Free, local OCR (no patient documents sent to a third party), supports Arabic data |
| **Playwright / pytest** | Real browser E2E / fast Python tests |

### A5. Why Python specifically? (short answer)
Because machine learning, OCR and data libraries (scikit-learn, pandas, OpenCV, Tesseract wrappers) are mature in Python, so the same language trains the model and serves predictions — no re-implementation, no translation errors between training and serving.

### A6. Important terms to memorise
RLS · JWT · RAG · embedding · cosine similarity · chunking · pipeline · data leakage · cross-validation · GridSearchCV · stratified split · confusion matrix · precision/recall/F1 · ROC-AUC · overfitting · magic bytes · signed URL · service role · SSE · OCR confidence · prompt injection.

### A7. Common mistakes students make
- Saying the model "diagnoses" — it gives a **score** from an educational model.
- Quoting the best *test* score as the selected model — selection was by CV on the training split.
- Claiming X-ray analysis or ECG waveform AI exists — it does **not**.
- Saying Gemini reads the uploaded files — it never does.
- Claiming deployment/live Gemini tests happened — they did not.
- Saying "RLS is in the app code" — it is in the database.

## Part B — Walkthrough topics

### B1. How authentication works
Supabase Auth stores the user and password hash, requires email confirmation, and issues a JWT. A DB trigger inserts a `profiles` row with role `patient`. The browser keeps the session in cookies (`@supabase/ssr`); `proxy.ts` refreshes it and redirects anonymous users from `/app`. FastAPI calls `auth.get_user(token)` (server-side verification), then reads `profiles.role/status`. Admin promotion is only possible with the service role (SQL), never from the UI/API a patient can reach.

### B2. How the database works
Tables in the ERD; foreign keys with `ON DELETE CASCADE` from `profiles`; enum types; CHECK constraints; indexes on `(user_id, created_at)`; pgvector HNSW index on `medical_knowledge.embedding`. RLS policies say `user_id = auth.uid()`; the user's JWT is passed to Postgres, so even buggy application code can't leak other users' rows.

### B3. How Gemini works here
The server sends the system prompt (safety rules), recent history and retrieved sources to `generate_content_stream`; chunks stream back to the browser as SSE. Embeddings (768-d) turn text into vectors for search. The key is a server env var. No key → 503 with instructions.

### B4. What RAG means
Retrieval-Augmented Generation: **retrieve** relevant approved text, **augment** the prompt with it, **generate** an answer that cites it. Reduces hallucination, allows showing sources and review dates.

### B5. How OCR works
Image → grayscale → upscale → denoise → adaptive threshold (OpenCV) → Tesseract returns words + confidence → our parsers (regex) turn lines into structured values → low confidence/unknowns become warnings, never invented values.

### B6. How the ML model was trained
`python -m ml.train`: load 303 rows → missing `?` → impute/encode/scale in a `Pipeline` → stratified 80/20 split → grid search with 5-fold CV on train → evaluate once on test → choose by CV AUC (Logistic Regression) → save with joblib. **Actual results:** see `05_machine_learning.md` (e.g., LR test accuracy 0.8689, recall 0.9286, ROC-AUC 0.9578 on 61 test patients).

### B7. How the algorithms work (30-second versions)
LR: weighted sum → sigmoid → probability. Tree: yes/no questions minimising Gini. Forest: many trees voting. SVM: widest-margin boundary, RBF kernel for curves.

### B8. How performance was evaluated
Accuracy, precision, recall, F1, ROC-AUC, confusion matrix on the held-out 61 patients, plus CV AUC on training data for selection. Limitations: tiny test set, one site.

### B9. How the frontend communicates with the backend
`lib/api.ts` attaches the Supabase access token and calls same-origin `/api/*` (rewritten to FastAPI in dev, routed by `vercel.json` in production). Errors use one JSON shape. Chat uses streaming SSE; uploads use XHR for progress.

### B10. How deployment works (target)
GitHub → Vercel builds Next.js and the Python function; Supabase hosts DB/Auth/Storage (`db push`); env vars hold secrets; OCR runs as a Docker worker. **Not yet deployed.**

### B11. Security and medical safety
Defence in depth: RLS, server checks, private buckets + signed URLs, validated uploads, rate limits, consent, audit logs, emergency regex, safe system prompt, human confirmation for OCR, constant disclaimers.

## Part C — Viva questions and answers (65)

Format: **Q** → answer. «ع» = simple Arabic explanation. ★ = difficult technical question.

### C1. General Project

**Q1. What is MediGuide AI and who is it for?** An educational cardiovascular-health platform for patients (and, in future, clinics). It explains, cites and organises information; it does not diagnose. «ع: منصة تثقيف لصحة القلب للمرضى.»

**Q2. What problem does it solve?** Patients can't understand reports/prescriptions, and generic AI chatbots mix education with unsafe advice and no sources/privacy. We combine safe explanations, document understanding, medication checks and strict privacy. «ع: المريض لا يفهم تقاريره، والشات العادي قد يعطي نصيحة خطرة بلا مصادر؛ نحن نجمع الشرح الآمن والخصوصية.»

**Q3. What is actually implemented vs planned?** Implemented: auth, RLS database, private storage, chat+RAG pipeline (needs Gemini key and approved sources), ML model + API, OCR for lab/ECG/prescription, medication review, admin, bilingual UI, tests. Planned: X-ray classifier, ECG waveform AI, richer interaction data, real deployment, clinical validation. «ع: المنفّذ: الدخول، قاعدة البيانات، الشات، النموذج، OCR. المؤجَّل: الأشعة وموجات القلب والنشر.»

**Q4. Is it a medical device?** No. It is educational/research software and deliberately avoids diagnostic claims; real use would need validation and regulatory approval (EDA in Egypt). «ع: لا، هو للتثقيف فقط وأي استخدام حقيقي يحتاج اعتمادًا.»

**Q5. What would you do next?** Run against real Gemini, load WHO/AHA sources, deploy, collect more data, add independent validation. «ع: تجربة Gemini الحقيقية، مصادر WHO/AHA، النشر، والتحقق الطبي.»

### C2. Requirements

**Q6. Give three functional and three non-functional requirements.** FR: register with email verification; upload and OCR lab report; emergency warning with 123. NFR: patients can't access others' data; model not trained per request; graceful errors when keys are missing. (See RTM.) «ع: أمثلة: تسجيل بالبريد، قراءة تحليل، تحذير الطوارئ 123.»

**Q7. What is a traceability matrix and why include it?** A table linking each requirement to code, database objects and tests, proving every requirement is implemented and verified. «ع: جدول يربط كل متطلب بالكود والاختبار ليثبت أنه منفّذ.»

**Q8. What is in scope and out of scope?** In: listed in section 5; out: diagnosis, X-ray/ECG AI, DICOM, handwriting, clinical use. «ع: داخل النطاق ما نفّذناه، وخارجه التشخيص وتحليل الأشعة والاستخدام الإكلينيكي.»

**Q9. How do you know a requirement is met?** By a named test (e.g., FR-12 → `test_rag_only_approved_chunks_retrieved`). «ع: بوجود اختبار باسمه يثبت المتطلب.»

### C3. UML and Flowcharts

**Q10. Which diagrams did you make and are they real?** Use case, class/module, sequence (auth, chat, upload, prescription), DFD 0/1, ERD, architecture, deployment, ML/RAG/OCR/ECG/X-ray flows. Each follows real functions/routes; planned parts are drawn dashed and labelled. All 16 render with Mermaid. «ع: الرسومات تتبع الكود الفعلي، وما لم يُنفَّذ مرسوم بخط متقطع ومكتوب 'مستقبلي'.»

**Q11. Explain the chat sequence.** Browser → `/api/chat` → verify token/consent → store message → emergency check → embed query → pgvector search → Gemini stream → save answer → `done`. «ع: يتحقق من الهوية والموافقة، يفحص الطوارئ، يبحث في المصادر، ثم يبث إجابة Gemini ويحفظها.»

**Q12. What is a DFD vs a flowchart?** DFD shows *data* moving between processes/stores/entities; a flowchart shows *step order/decisions*. «ع: DFD يوضح حركة البيانات، والـflowchart يوضح ترتيب الخطوات.»

**Q13. Why is the ECG waveform box dashed?** Because it is future work; showing it solid would claim a feature that doesn't exist. «ع: لأنه غير منفّذ، ورسمه كاملاً سيكون ادعاءً كاذبًا.»

**Q14. Difference between use case "include" and "extend"?** Include: always happens (upload includes analyze); extend: optional addition (prescription review can extend from OCR). «ع: include تحدث دائمًا، وextend اختيارية.»

### C4. Frontend

**Q15. Why Next.js App Router?** Server components/layouts for auth and first-paint RTL, file-based routing, Vercel integration. «ع: يعطينا صفحات من السيرفر وحماية للمسارات وتكاملًا مع Vercel.»

**Q16. How is Arabic RTL implemented?** Server reads the `locale` cookie and sets `<html lang dir>`; CSS uses logical properties (`ps-`, `me-`, `border-e`); the dictionary has both languages; E2E tests check `dir`. «ع: السيرفر يضبط اتجاه الصفحة من الكوكي والتنسيق يستخدم خصائص منطقية تنعكس تلقائيًا.»

**Q17. How do you protect routes?** `proxy.ts` (redirect when no session) **and** `app/app/layout.tsx` (server check + profile). The API enforces again — UI hiding is never the security. «ع: نحمي في المتصفح وفي السيرفر وفي الـAPI؛ إخفاء الزر وحده ليس حماية.»

**Q18. How is form validation done?** React Hook Form + Zod in the browser; Pydantic again on the server (never trust the client). «ع: نتحقق في المتصفح للراحة وفي السيرفر للأمان.»

**Q19. How do you stream chat to the UI?** `fetch` body reader parses SSE `data:` events and appends deltas. «ع: نقرأ الاستجابة قطعة قطعة ونضيفها للشاشة.»

**Q20. ★ Why XHR for uploads when fetch exists?** `fetch` can't report upload progress; XHR's `upload.onprogress` can. «ع: لأن XHR يعرف نسبة الرفع بينما fetch لا يعرفها.»

**Q21. What is `proxy.ts`?** Next.js 16's renamed middleware; runs before routes to refresh cookies and redirect. «ع: هو middleware بالاسم الجديد: يجدد الجلسة ويوجّه غير المسجلين.»

### C5. Backend

**Q22. Why FastAPI?** Type hints → validation and docs, async/SSE, light enough for serverless. «ع: يتحقق من المدخلات تلقائيًا ويولد التوثيق ويدعم البث.»

**Q23. How is authorization done?** `get_current_user` verifies the JWT with Supabase, loads role/status; `AdminUser`/`ReviewerUser` dependencies check role; suspended → 403. «ع: نتحقق من الرمز ونقرأ الدور ونمنع الموقوف.»

**Q24. ★ Why call the database with the user's JWT instead of the service role?** So RLS still protects data if our code has a bug; the service role bypasses RLS and is used only for audit, admin listing and account deletion. «ع: حتى لو أخطأ الكود، قاعدة البيانات تحمي بيانات المستخدمين.»

**Q25. How are errors handled?** Global handlers return `{error:{code,message,fields}}`; validation errors never echo inputs; unexpected errors log only exception type. «ع: كل الأخطاء بشكل JSON موحّد دون كشف بيانات.»

**Q26. What does rate limiting do and what's its weakness?** Sliding window per user; in-memory so it's per serverless instance — a global limiter (Redis) is future work. «ع: تحدّ عدد الطلبات، لكنها محلية لكل نسخة.»

**Q27. How do you avoid logging medical data?** Logs include exception class names and IDs only; audit metadata never contains text from documents or chat. «ع: نسجل نوع الخطأ فقط لا محتوى طبي.»

### C6. Python

**Q28. Why Python for the backend and ML?** Same language, mature libraries, readability. «ع: نفس اللغة للتدريب والخدمة ومكتبات ناضجة.»

**Q29. What is a virtual environment and why used?** Isolated dependency set (`.venv`) so versions are reproducible. «ع: بيئة معزولة لتثبيت نفس الإصدارات.»

**Q30. What is type hinting used for here?** FastAPI/Pydantic read hints to validate/parse requests. «ع: FastAPI يقرأها ليتحقق من البيانات.»

**Q31. ★ What does `Depends` do?** FastAPI dependency injection: runs `get_current_user`/limiters before the route and passes results in. «ع: تشغّل دوال التحقق قبل الدالة وتمرّر النتيجة.»

### C7. Libraries

**Q32. Name the key Python libraries and what each does.** fastapi (API), pydantic (validation), supabase (DB/Auth/Storage client), google-genai (Gemini), scikit-learn/pandas/numpy/joblib (ML), pillow/pypdf (files), opencv+pytesseract (OCR), httpx (HTTP). Table in §22. «ع: كل مكتبة ودورها موجودة في جدول القسم 22.»

**Q33. Any installed library you don't import?** Yes, and documented: python-multipart (needed by FastAPI forms), uvicorn (runner), react-dom/typescript/tailwind (toolchain/implicit), `@supabase/supabase-js` (peer dependency of `@supabase/ssr`). `PyJWT` is a transitive dependency we don't import. «ع: نعم وموثّقة: بعضها ضمني أو أدوات تشغيل أو معتمد عليه من مكتبة أخرى.»

**Q34. Did you use PaddleOCR or shadcn CLI?** No. Tesseract was used; shadcn-*style* components were written by hand. «ع: لا؛ استخدمنا Tesseract وكتبنا مكونات بنمط shadcn يدويًا.»

**Q35. What does `joblib` do and why not `pickle`?** Efficiently serialises scikit-learn objects (large NumPy arrays), standard in scikit-learn; both are unsafe to load from untrusted sources — our artifact is our own. «ع: joblib يحفظ النموذج بكفاءة، ولا نحمّل ملفات من مصدر غير موثوق.»

### C8. Machine Learning

**Q36. What is the task and the dataset?** Binary classification of heart-disease presence using UCI Cleveland: 303 patients, 13 features, 139 positive/164 negative after binarising `num>0`. «ع: تصنيف: هل يوجد مرض قلب؟ على 303 مريض و13 خاصية.»

**Q37. ★ How did you handle missing values?** `ca` (4) and `thal` (2) are `?` → imputed inside the pipeline (median / most frequent) so imputation is fitted on training folds only. «ع: القيم الناقصة تُعوَّض داخل خط المعالجة على بيانات التدريب فقط.»

**Q38. ★ What is data leakage and how did you avoid it?** Test information influencing training. We split first, put imputers/scalers/encoders inside the `Pipeline` (fitted per CV fold), tuned only on the training split, evaluated on test once, and **selected the model by CV score, not test score**. «ع: تسرب البيانات = الاختبار يؤثر على التدريب؛ منعناه بالتقسيم أولًا وبالـPipeline وباختيار النموذج بالتحقق المتقاطع.»

**Q39. Why stratified split?** Keeps class ratio equal in train and test, important for small data. «ع: ليبقى توزيع الحالات متساويًا بين التدريب والاختبار.»

**Q40. Why scale features?** LR and SVM are sensitive to feature magnitude (e.g., cholesterol ~250 vs `oldpeak` ~1). «ع: حتى لا تطغى الأرقام الكبيرة (كوليسترول) على الصغيرة.»

**Q41. Why one-hot encode `cp`, `slope`, `thal`?** They're categories without numeric order; one-hot avoids implying order. «ع: الفئات ليست مرتبة، فنحولها لأعمدة 0/1.»

**Q42. ★ Why was Logistic Regression selected although SVM had higher test accuracy?** Rule: highest 5-fold CV ROC-AUC on training data (LR 0.9069 vs SVM 0.9044 vs RF 0.8985); the test set is only 61 patients so differences are noise, and choosing by test would leak. «ع: اخترناه بنتيجة التحقق المتقاطع لا بنتيجة الاختبار الصغير (61 مريض).»

**Q43. Is 87% accuracy good enough for medicine?** No claim of clinical suitability: tiny single-site data, no external validation or calibration; it is a teaching/research model. «ع: لا؛ البيانات صغيرة وبلا تحقق خارجي فهو نموذج تعليمي.»

**Q44. Is the model retrained on each request?** Never; trained offline, loaded once and cached. «ع: لا، التدريب مرة واحدة خارج الخادم.»

### C9. Algorithms

**Q45. Explain logistic regression.** Linear combination → sigmoid gives probability; trained by minimising log-loss with L2 regularisation (`C`). «ع: يجمع الخصائص بأوزان ويحوّل الناتج لاحتمال بين 0 و1.»

**Q46. ★ Why do decision trees overfit and how did you limit it?** They can memorise the training set with deep splits; we tuned `max_depth` and `min_samples_leaf` by CV (selected depth 3, leaf 10). «ع: الشجرة العميقة تحفظ البيانات؛ حددنا العمق والحد الأدنى للأوراق.»

**Q47. How does a random forest reduce variance?** Averages many de-correlated trees (bootstrap + random feature subsets). «ع: يأخذ تصويت أشجار كثيرة فيقل التذبذب.»

**Q48. ★ What does the RBF kernel do in SVM and what do `C` and `gamma` control?** Implicitly maps to a high-dimensional space via `exp(−γ‖x−x′‖²)`; `C` trades margin width vs errors; `gamma` sets how local the influence of a point is (selected: C=1, gamma=0.01). «ع: RBF يرسم حدودًا منحنية؛ C يوازن بين الهامش والأخطاء وgamma يحدد تأثير النقطة.»

**Q49. ★ What is GridSearchCV?** Tries every hyper-parameter combination with cross-validation and returns the best by the scoring metric (ROC-AUC). «ع: يجرب كل التركيبات بالتحقق المتقاطع ويختار الأفضل.»

### C10. Evaluation Metrics

**Q50. Define precision, recall, F1.** Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 = harmonic mean. «ع: الدقة = الصحيح من التحذيرات؛ الاستدعاء = المرضى الذين وجدناهم.»

**Q51. Which matters most here?** Recall, because missing a sick patient is costlier than a false alarm — but a screening tool must also limit false alarms; we report both. «ع: الاستدعاء أهم لأن تفويت مريض أسوأ من إنذار كاذب.»

**Q52. ★ What does ROC-AUC mean intuitively?** The probability a randomly chosen sick patient gets a higher score than a randomly chosen healthy one; threshold-independent. «ع: احتمال أن يحصل مريض على درجة أعلى من سليم.»

**Q53. Read the LR confusion matrix.** TN 27, FP 6, FN 2, TP 26 (61 patients): accuracy (27+26)/61 = 0.8689; recall 26/28 = 0.9286; precision 26/32 = 0.8125. «ع: 27 سليم صحيح، 6 إنذار كاذب، 2 مريض فاتنا، 26 مريض صحيح.»

**Q54. ★ Why are the reported numbers uncertain?** 61 test patients → wide confidence intervals (one patient ≈ 1.6 percentage points); no repeated splits; single hospital. «ع: عدد المختبرين 61 فقط فالنتائج غير مؤكدة.»

### C11. Gemini

**Q55. What does Gemini do in the project and what doesn't it do?** Writes chat answers and makes embeddings. It never reads uploaded images/documents, never diagnoses, never sees the medical profile. «ع: يكتب الإجابة ويصنع التضمينات، ولا يرى ملفاتك ولا يشخّص.»

**Q56. What happens without an API key?** HTTP 503 `service_not_configured` with a setup hint — no fake answers. «ع: يظهر خطأ 503 برسالة إعداد، دون إجابات مزيفة.»

**Q57. ★ How do you defend against prompt injection?** Sources and user text are labelled untrusted in the prompt, system prompt says to ignore instructions inside them, Markdown is rendered without raw HTML, and retrieval is restricted to reviewer-approved text. Not adversarially tested — a stated limitation. «ع: نعامل النصوص كبيانات غير موثوقة ونقيّد المصادر المعتمدة.»

**Q58. Why consent before chat?** Chat text goes to Google (cross-border processing of potentially sensitive data); explicit consent is a requirement under data-protection principles. «ع: لأن النص يُرسل لجهة خارجية فنحتاج موافقة صريحة.»

**Q59. How is the emergency behaviour guaranteed?** A deterministic regex (English + Arabic) runs before and independently of the LLM and sends the 123 warning as the first SSE event. «ع: كود عادي يكشف كلمات الطوارئ ويعرض 123 فورًا قبل الذكاء الاصطناعي.»

### C12. RAG

**Q60. ★ Explain your RAG pipeline.** Clean → chunk (1200 chars, 150 overlap) → embed (768-d) → store in pgvector as `pending` → reviewer approves → query embedding → cosine search (≥0.45, top 5, approved only) → context to Gemini → sources returned with name, URL, dates. «ع: ننظف ونقطّع ونحوّل لأرقام ونخزن ثم نبحث ونعطي Gemini المصادر.»

**Q61. ★ Why cosine similarity and normalised vectors?** Direction (meaning) matters not length; with unit vectors cosine = dot product, and truncating embeddings to 768 dimensions breaks unit length, so we re-normalise. «ع: المعنى هو الاتجاه لا الطول، ونعيد التطبيع بعد تقليل الأبعاد.»

**Q62. Is the knowledge base populated?** No — it ships empty; the admin must add real sources. We refused to fabricate citations or copy unreviewed text. «ع: فارغة؛ لم نخترع مصادر.»

**Q63. How do you handle outdated information?** `last_reviewed_on` is stored and shown; automatic expiry is future work. «ع: نخزّن تاريخ المراجعة ونعرضه؛ الانتهاء التلقائي مستقبلي.»

### C13. OCR

**Q64. Why OpenCV before Tesseract?** Cleaning (denoise, adaptive threshold, upscale) measurably helps recognition on uneven photos. «ع: التنظيف يحسّن دقة القراءة.»

**Q65. How do you deal with uncertainty?** Confidence scores, low-confidence warnings, plausibility ranges, fuzzy-match flags, `null` for unknowns, user confirmation. Lab values are compared only with ranges printed on the report. «ع: نعرض الثقة ونحذّر ولا نخمّن ونطلب تأكيد المستخدم.»

**Q66. ★ Why is OCR in a separate worker?** Tesseract is a system binary that Vercel's Python runtime does not provide; the API delegates via a token-protected endpoint. «ع: Tesseract برنامج نظام غير متاح على Vercel فنشغله في حاوية.»

**Q67. Can it read handwriting?** No; flagged as unsupported and never guessed. «ع: لا؛ ننبّه ولا نخمّن.»

### C14. Database

**Q68. What is RLS?** PostgreSQL rules evaluated per row, e.g. `user_id = auth.uid()`; enforced by the database for every query made with a user's JWT. «ع: قواعد في قاعدة البيانات تحدد أي صفوف يراها كل مستخدم.»

**Q69. ★ How do you prevent a user making themselves admin?** No UPDATE of `role/status` allowed for non-admins (trigger `protect_profile_fields` raises), no INSERT/DELETE policies on `profiles`, and the signup trigger always assigns `patient`. Tested. «ع: لا يوجد تحديث للدور للمستخدم العادي، وتريجر يمنع التغيير.»

**Q70. Why are binary files not in PostgreSQL?** Large blobs hurt DB performance/backups; Storage serves files via signed URLs while the DB stores only the path. «ع: الملفات الكبيرة تُثقل القاعدة؛ نخزن المسار فقط.»

**Q71. What do the cascade foreign keys do?** Deleting a profile deletes all that user's rows, supporting the right to erasure. «ع: حذف المستخدم يحذف كل بياناته.»

**Q72. ★ Why can't an admin read a patient's conversations?** No admin policy exists on owner-only tables (privacy by design); admins see counts through the service role only. «ع: لا توجد سياسة قراءة للمدير على البيانات الخاصة.»

### C15. Supabase

**Q73. What Supabase services are used?** Auth (users, email verification), Postgres (data, RLS, pgvector), Storage (private buckets). «ع: الدخول، قاعدة البيانات، والتخزين.»

**Q74. Why signed URLs?** Buckets are private; a signed URL is a temporary (120 s) capability for one file. «ع: رابط مؤقت (120 ثانية) لملف واحد.»

**Q75. Where are the keys?** Publishable key in the browser; service-role key only in backend env vars; `.env.local` is git-ignored. «ع: المفتاح السري على السيرفر فقط.»

### C16. Security

**Q76. Name five security controls.** RLS, server-side auth, validated uploads (magic bytes), private storage + signed URLs, rate limiting/audit/consent. «ع: RLS، تحقق السيرفر، رفع آمن، تخزين خاص، حدود وتدقيق.»

**Q77. ★ Why validate by magic bytes, not by the MIME header?** The client controls the header; magic bytes show the real format; plus extension match and Pillow decode checks. «ع: رأس الملف يمكن تزويره، أما البايتات الأولى فتكشف النوع الحقيقي.»

**Q78. What security gaps remain?** No CSP, per-instance rate limit, no MFA, no virus scan, no enforced retention job, no pen-test. «ع: لا CSP ولا MFA ولا فحص فيروسات ولا اختبار اختراق.»

**Q79. How does account deletion work?** Backend deletes storage objects, then deletes the auth user; cascades remove rows; action audited. «ع: نحذف الملفات ثم المستخدم والصفوف تُحذف تلقائيًا.»

**Q80. Egyptian law?** Law 151/2020 requires lawful basis/consent and protection of sensitive data; we implement consent, minimisation and erasure; legal review is required before real deployment. «ع: القانون 151 لسنة 2020 يتطلب موافقة وحماية؛ ونحتاج مراجعة قانونية.»

### C17. Deployment

**Q81. How would you deploy?** Push to GitHub, import in Vercel, set env vars, `supabase db push`, optional Docker OCR worker. It is prepared but **not deployed**. «ع: GitHub ثم Vercel وSupabase؛ جاهز لكن لم يُنشر.»

**Q82. ★ What Vercel constraints shaped the design?** No Tesseract binary (→ worker); read-only/ephemeral disk (no writes); bundle size (325 MB measured, no OpenCV in the API bundle); function time (60 s); in-memory rate limit per instance; never retrain at deploy. «ع: لا Tesseract، لا كتابة على القرص، حجم الحزمة، ومهلة التنفيذ.»

**Q83. What is `vercel.json` for?** Rewrites `/api/*` to the Python function and bundles model/data files. «ع: يوجّه /api لدالة بايثون ويضم ملفات النموذج.»

### C18. Medical Safety

**Q84. What will the assistant never do?** Claim to be a doctor, diagnose, prescribe, stop/replace/change doses. «ع: لا يدّعي الطب ولا يشخّص ولا يصف ولا يغير الجرعات.»

**Q85. What if a user types "chest pain"?** Immediate warning with ambulance 123 before any other output. «ع: تحذير فوري باتصال 123.»

**Q86. Can the prescription module say a prescription is safe?** No; it lists warnings and always ends with the pharmacist/doctor notice; absence of warnings ≠ safe. «ع: لا؛ يعرض تحذيرات فقط ودائمًا يطلب مراجعة الصيدلي.»

**Q87. Why not use Gemini to describe X-rays?** General image descriptions aren't validated medical diagnosis and could mislead; X-ray analysis is future work. «ع: وصف الصور العام ليس تشخيصًا طبيًا معتمدًا.»

**Q88. How do you show the model is research-only?** Disclaimer in every result, "model score" wording, limitations list, model version and test metrics shown. «ع: عبارة 'درجة النموذج' والقيود والإصدار والتنبيه في كل نتيجة.»

### C19. Extra hard questions

**Q89. ★ A patient can POST someone else's `document_id` to `/analyze`. What happens?** The document query runs with the patient's JWT; RLS returns zero rows → 404 identical to "does not exist" (no information leak). Test: `test_lab_upload_ocr_end_to_end…`. «ع: قاعدة البيانات لا تُرجع صفوفًا فيظهر 404 كأنه غير موجود.»

**Q90. ★ Race/partial failure in upload?** If the DB insert fails after the storage upload, the file is removed to avoid orphans. «ع: إن فشل الحفظ في القاعدة نحذف الملف حتى لا يبقى يتيمًا.»

**Q91. ★ Why not calibrate probabilities?** Not done (limitation); the score is not presented as a calibrated probability. «ع: لم نعايره، ولذلك لا نسميه احتمالًا مؤكدًا.»

**Q92. ★ How would you evaluate answer quality of the chatbot?** Build a reviewed Arabic/English question set with expected key facts and source IDs, measure citation correctness, refusal behaviour and emergency recall, ideally with clinician raters. Not done yet. «ع: نبني أسئلة مراجعة ونقيس صحة الاستشهاد والرفض والطوارئ بمراجعة أطباء.»

*(92 questions in total; 23 are marked ★ difficult. Each answer ends with a simplified Arabic note «ع».)*

## Part D — Five-minute explanation (speak this)
"MediGuide AI is an educational cardiovascular-health platform with an Arabic-first interface. The problem: patients receive lab results, ECGs and prescriptions they can't understand, and general chatbots give unsafe, unsourced advice. Our solution has five parts. First, a Supabase-secured workspace: every patient's data is protected by Row Level Security in the database. Second, a chat assistant using Gemini with retrieval-augmented generation — it retrieves reviewer-approved sources from a pgvector database and cites them, and an emergency detector shows the 123 ambulance warning before any AI text. Third, a scikit-learn machine-learning model trained on the UCI Cleveland dataset — 303 patients; we compared four algorithms with cross-validation on the training split and evaluated on 61 held-out patients; the selected Logistic Regression reached 0.87 accuracy and 0.96 ROC-AUC — and we are careful to call this a research score, not a diagnosis. Fourth, document processing: uploads are validated and stored privately, OpenCV and Tesseract read printed lab values and ECG numbers, and anything uncertain is flagged rather than guessed. Fifth, a medication-safety review that finds duplicates, missing doses, allergy matches and known interaction classes, always asking the user to confirm OCR output and a pharmacist to verify decisions. We tested with 59 backend tests and 16 browser end-to-end tests, including real email verification. What's not done: live Gemini testing, a populated knowledge base, X-ray and ECG-waveform AI, and deployment — these are clearly listed as future work."

## Part E — Ten-minute technical explanation (outline with key sentences)
1. **Architecture (1.5 min):** Browser → Next.js (proxy.ts guard) → FastAPI (`/api`) → Supabase (Auth, Postgres+RLS+pgvector, Storage); Gemini and DailyMed external; OCR worker for Tesseract. "The API uses the *user's* JWT so RLS still applies."
2. **Database & security (2 min):** 12 tables; owner-only policies; admin has no read policy on private rows; triggers prevent role escalation and cross-tenant links; private buckets with `<uid>/` path policy; signed URLs 120 s; audit log.
3. **ML (2.5 min):** pipeline stages; leakage prevention; four models and tuned params; results table; why LR was selected; why test numbers are uncertain; saved with joblib; served read-only.
4. **AI/RAG (2 min):** consent → emergency regex → embed → `match_medical_knowledge` (approved only, cosine ≥ 0.45) → Gemini stream → citations. Admin approval workflow. Honest status: no key, empty corpus.
5. **OCR & documents (1 min):** magic-byte validation; OpenCV + Tesseract; parsers; never invent values; X-ray no diagnosis.
6. **Testing & deployment (1 min):** 59 + 16 tests, build verified, Vercel-like clean-env test, 325 MB; deployment prepared but not executed.

## Part F — "Explain MediGuide AI Like I Built It Myself"
"I started from a simple question: how can AI help a patient understand heart-health information without ever pretending to be a doctor? That shaped every decision. I put safety first and made it deterministic where it matters: the emergency warning isn't left to the language model — it's plain code that checks the message and shows 123 immediately. For privacy I let the database enforce the rules, not just my code: with Supabase Row Level Security every patient's rows are visible only to them, and I even made sure administrators can't read private medical records. I call the database with the patient's own token, so a bug in my API can't leak someone else's data — I wrote tests where a second user tries to read, edit and delete the first user's records and fails.

For the AI, I used retrieval-augmented generation: the assistant only quotes sources that a reviewer has approved, and I show the source name, link and review date. I'll be honest — I built the pipeline and tested it with a stand-in for Gemini, but I haven't run it against the live service because I don't have an API key yet, and the knowledge base still needs real WHO and AHA texts.

For machine learning I used Python and scikit-learn on the UCI Cleveland dataset. I put preprocessing inside a pipeline so there's no data leakage, tuned each of four algorithms with cross-validation only on training data, and picked the final model by cross-validation, not by the test score. Logistic Regression got about 0.87 accuracy and 0.96 AUC on 61 test patients — good for a classroom model, but I describe it as a research score because the data is small, old and from one hospital.

For documents, I validate files by their real content, store them privately, and use OpenCV with Tesseract to read printed numbers. If the text isn't clear, the app says so instead of guessing, and for X-rays it deliberately does not interpret the image. The medication review checks duplicates, missing doses, allergies and a few well-documented interaction classes, and always tells the user a pharmacist must verify.

Finally I tested it: 59 backend tests, 16 browser tests — including sign-up with a real verification email — and a production build. What's left is deployment, a live Gemini test, real sources, and clinical validation before anyone could rely on it."

## Part G — Final examination preparation checklist
- [ ] I can draw the architecture and name each arrow's purpose.
- [ ] I can explain RLS with the `user_id = auth.uid()` example and why the JWT is passed through.
- [ ] I can state: 303 rows, 13 features, 242/61 split, 4 models, selected LR, and read the confusion matrix.
- [ ] I can explain why the test score was not used for selection.
- [ ] I can explain RAG steps and what is missing (key, corpus).
- [ ] I can list what is implemented vs future work without bluffing (X-ray, ECG waveform, deployment).
- [ ] I can describe every library's role (and the unused/implicit ones).
- [ ] I can explain emergency handling, consent, signed URLs, magic bytes.
- [ ] I can run the app (`supabase start`, `uvicorn`, `npm run dev`) and demo: register → risk form → upload lab → medication review.
- [ ] I know the test counts (59 backend, 16 E2E) and what they do **not** cover.
- [ ] I reviewed the Arabic explanations and practised the five-minute talk aloud.

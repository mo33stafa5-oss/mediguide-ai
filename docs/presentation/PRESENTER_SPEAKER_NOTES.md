# Presenter Speaker Notes — MediGuide AI (≈ 11 minutes)

Speaking times sum to ≈ 10:50 minutes (target 8–12). English text is for speaking; Arabic lines are study explanations. Screenshots are real captures of the app with synthetic data. Metrics come from `ml/reports/evaluation.json`.

## Slide 1 — Title
**What the slide shows:** Logo, name, slogan.

**What I should say:** “Good morning. I'm presenting MediGuide AI — an educational platform that helps patients understand heart-health information safely, in Arabic and English.”

**Technical explanation:** The name combines Medi(cal) + Guide; the slogan (Arabic) means 'clearer information, better decisions, easier health'.

**Possible professor question and suggested answer:** Is it a real medical product? — No. It is educational/research software; real use needs clinical validation and regulatory approval.

**شرح للدراسة:** عنوان المشروع: منصة تثقيف صحي للقلب وليست طبيبًا.

**Speaking duration:** 0:30

## Slide 2 — Introduction
**What the slide shows:** Real Arabic landing page screenshot.

**What I should say:** “It is a bilingual web app: each patient gets a private workspace with chat, a risk model, document upload and medication review. It never diagnoses or prescribes.”

**Technical explanation:** Next.js 16 front end with Arabic RTL default, FastAPI back end, Supabase for auth/data/files.

**Possible professor question and suggested answer:** Why Arabic first? — The target users; RTL is set on the server from a cookie so it renders correctly on first paint.

**شرح للدراسة:** تطبيق ثنائي اللغة مع مساحة خاصة لكل مريض.

**Speaking duration:** 0:45

## Slide 3 — Problem Statement
**What the slide shows:** Four problem cards.

**What I should say:** “Patients get lab values and prescriptions they can't interpret. General chatbots can hallucinate, cite nothing and have no emergency protocol, and medical files need real isolation.”

**Technical explanation:** The gap: safe, sourced, private, Arabic explanations plus document understanding.

**Possible professor question and suggested answer:** How do you know chatbots hallucinate? — It's a well-documented LLM behaviour; that's why we use retrieval and refuse unsupported claims.

**شرح للدراسة:** المشكلة: عدم فهم النتائج، ونصائح غير آمنة، وخصوصية ضعيفة.

**Speaking duration:** 0:45

## Slide 4 — Objectives
**What the slide shows:** Six objectives.

**What I should say:** “Six goals: database-enforced privacy, safe cited chat, a real ML model, OCR with uncertainty, medication-safety review, and a tested, documented codebase.”

**Technical explanation:** Each objective maps to a requirement and test in the traceability matrix.

**Possible professor question and suggested answer:** How did you verify objectives? — Named tests per requirement (RTM in the documentation).

**شرح للدراسة:** أهداف ستة تقابلها اختبارات.

**Speaking duration:** 0:40

## Slide 5 — Proposed Solution
**What the slide shows:** Five module cards.

**What I should say:** “Five modules share one secure database: chat with RAG, the risk model, documents, medication safety and a privacy core.”

**Technical explanation:** Modules are separate in code: services/, ocr/, ml/, supabase/.

**Possible professor question and suggested answer:** Is everything finished? — Implemented and tested locally; live Gemini, real knowledge sources and deployment are pending.

**شرح للدراسة:** خمس وحدات تعمل فوق قاعدة بيانات آمنة واحدة.

**Speaking duration:** 0:40

## Slide 6 — Main Features
**What the slide shows:** Real dashboard (desktop) and mobile screenshots, synthetic user.

**What I should say:** “This is the actual running app: dashboard with counts and a medical timeline, and the responsive mobile layout with bottom navigation.”

**Technical explanation:** Dashboard reads RLS-filtered rows directly from Supabase; tested at a phone viewport for no horizontal overflow.

**Possible professor question and suggested answer:** Did you fake the data? — No: synthetic account created through the real sign-up path; screenshots are captured by a script (tests/e2e/capture-screenshots.mjs).

**شرح للدراسة:** لقطات حقيقية من التطبيق.

**Speaking duration:** 0:45

## Slide 7 — System Architecture
**What the slide shows:** Real architecture diagram.

**What I should say:** “The browser talks to Next.js and, with its token, to FastAPI. FastAPI uses the user's JWT against Supabase so row-level security still applies. Gemini and DailyMed are external; Tesseract OCR runs in a Docker worker.”

**Technical explanation:** The service-role key is used only for audit, admin and deletion. Vercel deployment is prepared but not yet performed.

**Possible professor question and suggested answer:** Why a separate OCR worker? — Tesseract is a system binary Vercel doesn't provide.

**شرح للدراسة:** المتصفح ← Next.js ← FastAPI ← Supabase.

**Speaking duration:** 0:45

## Slide 8 — Technology Stack
**What the slide shows:** Four columns, from package.json / requirements.txt.

**What I should say:** “Only libraries actually installed and imported are listed. Python gives us ML, OCR and the API in one language; scikit-learn gives the four algorithms with one API.”

**Technical explanation:** Python: unified ecosystem. scikit-learn: Pipeline, GridSearchCV, small artifacts, no GPU.

**Possible professor question and suggested answer:** Why not deep learning? — 303 tabular rows; classical models are appropriate and deep nets would overfit.

**شرح للدراسة:** المكتبات المذكورة فقط هي المستخدمة فعلًا.

**Speaking duration:** 0:30

## Slide 9 — Python and Machine Learning
**What the slide shows:** Pipeline bullets.

**What I should say:** “We use the UCI Cleveland dataset: 303 patients, 13 features. Preprocessing sits inside a pipeline, so there is no leakage; tuning uses cross-validation on the training split only; the test set is used once.”

**Technical explanation:** Impute median/mode, one-hot categorical, standard-scale numeric; stratified 80/20 split, seed 42 (242/61).

**Possible professor question and suggested answer:** What is data leakage? — Test information influencing training; avoided by splitting first and fitting transforms inside CV folds.

**شرح للدراسة:** التدريب خارج الخادم، والـAPI يقرأ النموذج المحفوظ فقط.

**Speaking duration:** 0:45

## Slide 10 — ML Results
**What the slide shows:** Real results table + ROC chart.

**What I should say:** “These are real numbers from our run. Logistic Regression was selected by cross-validation and reached 0.869 accuracy, 0.929 recall and 0.958 ROC-AUC on 61 test patients. The SVM scores slightly higher on test, but we don't choose by test; and with 61 patients differences are noise.”

**Technical explanation:** Confusion matrix LR: TN 27, FP 6, FN 2, TP 26. Single split, single site, uncalibrated.

**Possible professor question and suggested answer:** Why not pick the SVM? — That would leak the test set into model selection. / Is 87% good? — Not a clinical claim; research score only.

**شرح للدراسة:** النتائج حقيقية من تشغيل فعلي؛ الاختبار 61 مريضًا فقط.

**Speaking duration:** 1:00

## Slide 11 — AI Chat and RAG
**What the slide shows:** RAG diagram and status box.

**What I should say:** “Before any AI text, a regular code check shows the 123 emergency warning if needed. We require consent, then retrieve only reviewer-approved sources from pgvector and let Gemini answer with citations. Honest status: tested with a stand-in for Gemini; the live service and the real knowledge base are still to do.”

**Technical explanation:** Embeddings 768-d, cosine ≥ 0.45, top 5; sources show name, URL, publish and review dates.

**Possible professor question and suggested answer:** What is RAG? — retrieve approved text, add to the prompt, generate with citations. / Why is the corpus empty? — I refused to fabricate citations; the admin must add reviewed text.

**شرح للدراسة:** RAG = امتحان 'كتاب مفتوح' للذكاء الاصطناعي.

**Speaking duration:** 0:45

## Slide 12 — Medical Document Processing
**What the slide shows:** Real OCR screenshot (synthetic lab report).

**What I should say:** “Uploads are validated by their real content and stored privately. OpenCV and Tesseract read printed values; lab results are compared only with the range printed on the report. For X-rays we don't interpret anything — that's future work.”

**Technical explanation:** OCR confidence 94.6/100 on this clean synthetic image; real photos will be lower. ECG: printed numbers only; prescriptions need user confirmation.

**Possible professor question and suggested answer:** Can it read handwriting or diagnose ECGs? — No, and it says so.

**شرح للدراسة:** لا نخمّن أي قيمة غير واضحة.

**Speaking duration:** 0:45

## Slide 13 — Database and Security
**What the slide shows:** ERD and controls.

**What I should say:** “Security is enforced in the database: row-level security on all twelve tables; admins can't read patients' private records; private storage with two-minute signed links; triggers prevent role escalation.”

**Technical explanation:** Policy example: user_id = auth.uid(). API uses the user's JWT so even a code bug can't leak rows.

**Possible professor question and suggested answer:** What about gaps? — No CSP or MFA yet, per-instance rate limit, retention job not implemented.

**شرح للدراسة:** الحماية في قاعدة البيانات نفسها.

**Speaking duration:** 0:40

## Slide 14 — Testing
**What the slide shows:** Four big numbers.

**What I should say:** “59 backend tests and 16 browser tests passed, including real email verification and tests where one patient tries to read another's data. Lint has no errors and the production build passes. Not covered: live Gemini, the Vercel runtime and noisy photos.”

**Technical explanation:** Vercel-like clean environment: 56 passed, 3 skipped (OCR needs Tesseract).

**Possible professor question and suggested answer:** Did every test pass first time? — No; I fixed several test and code issues along the way; the numbers are from the final runs.

**شرح للدراسة:** لا ندّعي نجاح شيء لم يُشغَّل.

**Speaking duration:** 0:35

## Slide 15 — Limitations and Future Work
**What the slide shows:** Two lists.

**What I should say:** “Limitations: educational, small single-site data, no X-ray or ECG-waveform analysis, small interaction list, not yet deployed. Future: real sources, public-dataset research models, licensed interaction data, validation and security hardening.”

**Technical explanation:** Each limitation appears in the documentation with its status label.

**Possible professor question and suggested answer:** What first before real use? — Clinical validation, legal/regulatory review, security audit.

**شرح للدراسة:** نكون صادقين بشأن ما لم يُنفَّذ.

**Speaking duration:** 0:40

## Slide 16 — Conclusion and Questions
**What the slide shows:** Summary.

**What I should say:** “MediGuide AI shows a secure, tested, bilingual platform with a real ML pipeline and a safety-first design. Thank you — I'm happy to take questions.”

**Technical explanation:** Be ready to open the repo and demo: register → risk form → upload lab → medication review.

**Possible professor question and suggested answer:** See the 92 questions in EXAMINATION_STUDY_GUIDE.md.

**شرح للدراسة:** شكرًا — جاهز للأسئلة.

**Speaking duration:** 0:20

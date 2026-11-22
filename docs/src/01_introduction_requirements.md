# Part 1 — Introduction, Requirements and Scope

## 1. Project Introduction
MediGuide AI is a bilingual (Arabic RTL / English LTR) web platform for **cardiovascular health education**. A patient registers, gets a private medical workspace and can: chat with an AI assistant that cites approved sources; run a research-grade heart-disease risk model; upload lab reports, ECGs, X-rays and prescriptions; have printed values extracted by OCR; and review a prescription for duplicates, missing doses, allergy matches and known interaction classes.

It is **educational and research software**. It never diagnoses, prescribes, or advises changing doses, and says so in the UI, in the API responses and in the AI system prompt.

> **بالعربي:** ميدي جايد منصة تساعد المريض على *فهم* معلومات صحة القلب (شات، تحاليل، روشتة). هي **ليست طبيبًا** ولا تُشخّص ولا تصف أدوية.

Technology: Next.js 16 (React 19, TypeScript, Tailwind 4) front end; FastAPI (Python 3.12) back end; Supabase (PostgreSQL + RLS + pgvector + Auth + Storage); scikit-learn model; Tesseract/OpenCV OCR; Google Gemini for chat and embeddings.

## 2. Background and Motivation
Cardiovascular disease is the leading cause of death worldwide (WHO). Patients routinely receive lab values, ECG printouts and prescriptions they cannot interpret, and Arabic-language, source-cited explanations are scarce. General chatbots can hallucinate medical facts and have no emergency protocol. The motivation is a tool that (1) explains, (2) cites, (3) refuses unsafe requests, (4) keeps data private, and (5) is honest about uncertainty. It is also a teaching project that exercises Python ML, OCR, RAG, databases and full-stack engineering together.

## 3. Problem Statement
Patients cannot easily understand cardiovascular information in their own language, and existing AI tools mix education with unsafe pseudo-diagnosis, lack source attribution, and mishandle private data. There is no integrated, privacy-preserving workspace that combines safe Arabic/English explanations, document understanding and medication-safety checks with explicit uncertainty handling.

## 4. Project Objectives
1. Build a secure multi-tenant platform where each patient only ever sees their own data (RLS). **[Implemented]**
2. Provide a medical chat assistant with emergency handling and cited retrieval. **[Implemented; Gemini key + corpus required to run]**
3. Train, evaluate and serve a real scikit-learn heart-disease model with honest metrics. **[Implemented]**
4. Extract printed values from lab/ECG/prescription documents with uncertainty flags. **[Implemented]**
5. Provide a medication-safety review with human confirmation. **[Implemented — limited rule base]**
6. Deliver a deployable, tested codebase and a complete academic package. **[Implemented; deployment itself pending credentials]**

## 5. Project Scope — IN
| Area | In scope | Status |
|---|---|---|
| Accounts | Register, email verification, login/logout, password recovery, profile, account deletion, data export, suspend (admin), roles patient/admin/medical_reviewer | Implemented |
| Chat | Streaming Gemini chat, conversation history, delete, copy, suggestions, Markdown, emergency banner (123), consent gate, source display | Implemented (needs key) |
| RAG | Ingest → clean → chunk → embed → pgvector → approved-only retrieval → attribution; admin approval UI | Implemented (corpus empty) |
| ML | UCI Cleveland dataset, 4 algorithms, tuned without leakage, saved pipeline, `/api/predict`, `/api/model-info` | Implemented |
| Documents | JPG/PNG/PDF upload, type-specific workflows, private buckets, signed URLs, safe deletion | Implemented |
| OCR | Tesseract + OpenCV (worker), PDF text layer, lab/ECG/prescription parsers | Implemented |
| Medication safety | Duplicates, missing dosage/frequency, allergy match, curated interaction rules, DailyMed lookup, human confirmation | Partially Implemented |
| Admin | Users, roles, suspend, knowledge approval, system health, ML evaluation, audit log | Implemented |
| i18n / UI | Arabic RTL default, English LTR, light/dark, responsive, SVG logo | Implemented |

## 6. Project Scope — OUT
| Item | Reason / status |
|---|---|
| Diagnosis, treatment advice, prescribing, dose changes | Unsafe; intentionally refused everywhere |
| X-ray interpretation (any classifier or Gemini description) | **Planned / Future Work.** Only upload, validation, metadata |
| ECG waveform classification | **Planned / Future Work.** Only printed-number OCR |
| DICOM files | No processing pipeline; rejected by magic-byte check |
| Handwritten prescription recognition | Tesseract is unreliable; handwriting is flagged, never guessed |
| Live drug-interaction database | NLM retired the RxNav interaction API; only a small curated list exists |
| Clinical validation / regulatory approval | Required before any real use |
| Appointment booking, hospital white-label, wearables | Shown in the visual reference image but not requested as implemented scope |
| Medical Reviewer dashboards beyond knowledge approval | Role exists; only knowledge ingest/approval is reviewer-specific |

## 7. Functional Requirements
| ID | Requirement | Status |
|---|---|---|
| FR-01 | A visitor can register with name, email, password (≥8, letters+digits) and must accept the educational disclaimer. | Implemented |
| FR-02 | Email must be verified before first login. | Implemented (Supabase `enable_confirmations`) |
| FR-03 | Users can log in, log out and recover a forgotten password. | Implemented |
| FR-04 | `/app/*` pages require an authenticated session. | Implemented (`proxy.ts` + server layout) |
| FR-05 | Users edit profile, medical profile (allergies, conditions…) and language. | Implemented |
| FR-06 | Users can export all their data and delete their account and files. | Implemented |
| FR-07 | Administrator can list users, change role, suspend/activate. | Implemented |
| FR-08 | Chat supports new/history/delete conversations, timestamps, copy, suggestions, Markdown, streaming. | Implemented |
| FR-09 | Chat requires explicit AI-processing consent. | Implemented |
| FR-10 | Emergency phrases (EN/AR) trigger an immediate warning with ambulance 123 before any AI output. | Implemented |
| FR-11 | Answers show source name, URL, publication date, last-review date and excerpt when sources are retrieved. | Implemented |
| FR-12 | Only reviewer-approved knowledge chunks are retrievable. | Implemented |
| FR-13 | Reviewer/admin can ingest text sources and approve/reject chunks. | Implemented |
| FR-14 | Heart-risk form validates every field and returns score, model version, explanation, limitations, recommendations, disclaimer. | Implemented |
| FR-15 | Users upload JPG/PNG/PDF (≤20 MB) per document type with preview and progress. | Implemented |
| FR-16 | Uploads are validated by content, stored privately and viewable only by short-lived signed URL. | Implemented |
| FR-17 | Lab OCR extracts test, value, unit, printed reference range and compares **only** to that range. | Implemented |
| FR-18 | ECG OCR extracts printed HR/PR/QRS/QT/QTc with plausibility checks. | Implemented |
| FR-19 | Prescription OCR proposes medications; the user must confirm before saving. | Implemented |
| FR-20 | Medication review reports duplicates, missing dose/frequency, allergy matches, interaction classes with sources, and a pharmacist notice. | Implemented |
| FR-21 | X-ray uploads are validated and stored; no diagnosis is produced. | Implemented (by design) |
| FR-22 | Dashboard shows counts and a medical timeline. | Implemented |
| FR-23 | Admin sees API health, storage buckets, model version, evaluation chart, audit log. | Implemented |
| FR-24 | Arabic RTL and English LTR with live switching; light/dark mode. | Implemented |

## 8. Non-Functional Requirements
| ID | Requirement | How it is met / verified |
|---|---|---|
| NFR-01 Security | Patients cannot read each other's data | RLS on every patient table; dedicated isolation tests (see §34) |
| NFR-02 Privacy | Private storage; no medical content in logs | Private buckets, signed URLs (120 s), logs record exception *type* only |
| NFR-03 Safety | Never diagnose/prescribe | System prompt, deterministic emergency regex, UI disclaimers, tests |
| NFR-04 Integrity | Never fabricate values | Parsers return `unknown`/null; tests assert no invented ranges |
| NFR-05 Performance | Model not trained per request | Inference-only `ml_service` (cached) |
| NFR-06 Portability | Deployable to Vercel | `vercel.json`, root `requirements.txt` (325 MB installed, measured) — not yet deployed |
| NFR-07 Usability | Responsive, bilingual, accessible | Playwright mobile/RTL tests; aria roles |
| NFR-08 Maintainability | Modular monorepo, typed, tested | Separate `backend/`, `ml/`, `app/`, `supabase/`, `tests/` |
| NFR-09 Reliability | Graceful degradation | Missing keys/services return structured 503 with setup hint |
| NFR-10 Auditability | Sensitive actions logged | `audit_logs` rows for upload/analyze/view/delete/admin |

## 9. Requirements Traceability Matrix
| Requirement | Code | Database | Test |
|---|---|---|---|
| FR-01..03 | `app/(auth)/*`, `app/auth/callback/route.ts` | `profiles`, trigger `handle_new_user` | `tests/e2e/i18n-auth.spec.ts` (register→Mailpit email→login), `test_profile_auto_created_as_patient` |
| FR-04 | `proxy.ts`, `app/app/layout.tsx` | – | `protected routes redirect…` (E2E) |
| FR-05 | `app/app/profile/page.tsx` | `user_medical_profiles` | `profile save and allergy persistence` |
| FR-06 | `routers/admin.py::delete_account/export_account` | cascade FKs | `test_account_export_and_deletion`, E2E deletion |
| FR-07 | `routers/admin.py::update_user` | `protect_profile_fields` trigger | `test_admin_overview_and_user_management`, `test_user_cannot_escalate_role` |
| FR-08..11 | `routers/chat.py`, `services/{safety,rag,gemini}.py`, `app/app/chat` | `conversations`, `messages` | `test_chat_stream_persist_and_isolation`, `test_chat_emergency_warning_first_with_123`, E2E chat |
| FR-12,13 | `routers/admin.py::ingest/set_status` | `medical_knowledge`, `match_medical_knowledge` | `test_rag_only_approved_chunks_retrieved` |
| FR-14 | `routers/predict.py`, `app/app/risk` | `heart_risk_assessments` | `test_predict_*`, E2E risk |
| FR-15,16 | `routers/documents.py`, `ocr/validate.py` | `medical_documents`, storage policies | `test_upload_validation_rejects_bad_files`, `rejects a fake image file` |
| FR-17,18 | `ocr/parsers.py` | `medical_analysis_reports` | `test_lab_flags_only_with_printed_range`, `test_ecg_*`, OCR integration tests |
| FR-19,20 | `routers/prescriptions.py`, `services/drugs.py` | `prescriptions`, `medication_records` | `test_prescription_*`, `test_duplicate_allergy_*`, E2E medication |
| FR-21 | `routers/documents.py` (xray branch) | – | `test_xray_workflow_never_diagnoses` |
| FR-22,23 | `app/app/page.tsx`, `app/app/admin/page.tsx` | – | E2E admin/dashboard |
| FR-24 | `lib/i18n/*`, `components/toggles.tsx` | – | E2E RTL/LTR/dark/mobile |

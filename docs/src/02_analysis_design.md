# Part 2 — Analysis and Design

## 10. System Analysis
**Problem decomposition.** Five concerns, each isolated in code: (1) identity and tenancy, (2) conversational AI with retrieval, (3) statistical prediction, (4) document understanding, (5) medication safety. They share one database and one authentication model.

**Key design decisions (and why)**
| Decision | Reason |
|---|---|
| Database access uses the **caller's JWT**, not the service role | Postgres RLS then enforces isolation even if application code has a bug |
| Service role only for audit log, admin listing, account deletion | Minimises blast radius; key never reaches the browser |
| Model trained offline, artifact committed (≈ small joblib) | No training at request/deploy time; lightweight for serverless |
| OCR in a separate Docker worker | Tesseract is a system binary, unavailable on Vercel |
| Emergency detection by regex **before** the LLM | Deterministic, instant, cannot be skipped by model behaviour |
| Retrieval only from `approved` chunks | Prevents unreviewed text from being cited as authoritative |
| OCR output never auto-saved as truth | `user_confirmed` required; saved rows have `verified=false` |

## 11. Stakeholder Analysis
| Stakeholder | Interest | Influence | Needs |
|---|---|---|---|
| Patient | Understand heart-health information safely | High | Clear Arabic, privacy, no false reassurance |
| Medical reviewer | Quality of knowledge base | Medium | Approve/reject sources, see provenance |
| Administrator | Operate the platform | High | User management, health, audit |
| Professor / examiner | Academic rigour | High | Real implementation, honest results, documentation |
| Treating doctor / pharmacist | Not a user, but final authority | High | App must defer to them |
| Regulators (Egypt) | Data protection, medical-software rules | High | Consent, minimisation, no unvalidated diagnostic claims |
| Third-party providers (Google, Supabase) | Data processors | Medium | Terms, data-processing safeguards |

## 12. Use Case Model
{{DIAGRAM:02_use_case}}

## 13. Detailed Use Case Specifications
**UC-01 Register and verify.** *Actor:* Visitor. *Pre:* none. *Main flow:* 1) enters name, email, password, ticks disclaimer; 2) client validates (Zod); 3) Supabase `signUp` stores user, trigger creates `profiles` row with role `patient`; 4) email sent; 5) user clicks the link; 6) session created, redirect to `/app`. *Alternates:* weak password → inline error; unverified login → "Email not confirmed". *Post:* a profile exists. *Tested:* E2E registration test reads the real email from Mailpit.

**UC-03 Chat with assistant.** *Actor:* Patient. *Pre:* logged in, AI consent given, `GEMINI_API_KEY` configured. *Main flow:* see sequence diagram in §15. *Alternates:* (a) emergency phrase → deterministic 123 warning first; (b) no approved source → answer flagged "general information"; (c) Gemini error → SSE `error` event, partial text preserved; (d) rate limit 15/min → 429. *Post:* user and assistant messages stored with sources.

**UC-04 Heart-risk assessment.** *Main flow:* form (13 UCI fields, range-validated twice: Zod + Pydantic) → `POST /api/predict` → `ml_service.predict` → row saved → result with model version, test metrics of the selected model, limitations, recommendations, disclaimer. *Alternates:* artifact missing → 503 `model_missing`; invalid input → 422 with field names (values not echoed).

**UC-05/06 Upload and analyze document.** *Main flow:* §15 upload sequence. *Alternates:* wrong magic bytes / extension mismatch / > 20 MB / corrupt → 422; X-ray PDF → 422; OCR unavailable → 503 `ocr_unavailable` and document status `failed`; low OCR confidence → warnings.

**UC-07 Review prescription.** *Main flow:* optional import of OCR medications → user edits → `POST /api/prescriptions/review` → warnings/interactions/DailyMed → user confirms → save. *Alternates:* saving without confirmation → 422 `confirmation_required`.

**UC-10/11 Knowledge ingest and approval.** Reviewer/admin submits text with source metadata → chunks stored `pending` → approve/reject per chunk. Patients can neither see nor retrieve pending chunks.

**UC-12 Manage users.** Admin changes role/suspends. Cannot demote/suspend self (409). Suspended users receive 403 on every API call.

## 14. System Architecture
{{DIAGRAM:01_architecture}}

**Layers.** *Presentation* (Next.js pages, `components/`), *API* (FastAPI routers), *Domain services* (`services/`, `ocr/`), *Data* (Supabase). The browser talks to Supabase directly **only** for authentication and RLS-filtered reads (profile, lists); every action with business rules (predict, chat, upload, review, admin) goes through FastAPI.

> **بالعربي:** المتصفح يتكلم مع Supabase للدخول وقراءة بياناته فقط، وكل العمليات الحساسة تمر عبر FastAPI الذي يتحقق من الهوية والصلاحيات.

## 15. System Workflows
### 15.1 Authentication
{{DIAGRAM:12_auth_workflow}}
### 15.2 AI chat
{{DIAGRAM:04_chat_workflow}}
### 15.3 RAG
{{DIAGRAM:05_rag_workflow}}
### 15.4 Machine learning
{{DIAGRAM:06_ml_workflow}}
### 15.5 Medical upload
{{DIAGRAM:07_upload_workflow}}
### 15.6 OCR
{{DIAGRAM:08_ocr_workflow}}
### 15.7 ECG (Implemented: printed numbers; Planned: waveform)
{{DIAGRAM:09_ecg_workflow}}
### 15.8 X-ray (Implemented: validation + metadata; Planned: classifier)
{{DIAGRAM:10_xray_workflow}}
### 15.9 Prescription
{{DIAGRAM:11_prescription_workflow}}
### 15.10 Deployment (target architecture; not yet deployed)
{{DIAGRAM:13_deployment}}

## 16. UML Diagrams
- **Use case diagram:** §12.
- **Class/module diagram** (Python backend; the code is functional/modular, so "classes" are Pydantic models and service modules):
{{DIAGRAM:14_class_diagram}}
- **Sequence diagrams:** §15.1, 15.2, 15.5, 15.9 (each step corresponds to a real function call).
- **ER diagram:** §18.

## 17. Data Flow Diagrams
**Level 0 (context)**
{{DIAGRAM:15_dfd_level0}}
**Level 1**
{{DIAGRAM:16_dfd_level1}}

## 18. Entity Relationship Diagram
{{DIAGRAM:03_erd}}

## 19. Database Design
Source of truth: `supabase/migrations/20260101000000_core_schema.sql` and `…000100_storage.sql`. Everything below is **extracted from the live local database** by `docs/build_docs.py`.

**Design principles.** UUID primary keys; every private row carries `user_id` referencing `profiles(id)` with `ON DELETE CASCADE` (deleting a user erases their data); enum types for roles/status/document type; CHECK constraints bound all free values (e.g. `size_bytes ≤ 20 MiB`, `score between 0 and 1`); `updated_at` triggers; `jsonb` only for variable OCR/review payloads; binary files **never** stored in PostgreSQL (only `storage_path`).

**Security triggers.** `protect_profile_fields` blocks non-admins from changing `role`/`status`; `assert_same_owner` forbids attaching a message/report/medication to another user's parent row; `handle_new_user` always creates role `patient`.

### Tables, columns, constraints, indexes
{{DB_TABLES}}

### Row Level Security policies (live from `pg_policies`)
Owner-only tables give administrators **no** policy: an admin cannot read a patient's conversations, documents or assessments (tested).
{{RLS_POLICIES}}

### Vector search function
```sql
select * from match_medical_knowledge(query_embedding := '[...768 floats...]', match_count := 5, min_similarity := 0.45);
-- cosine similarity = 1 - (embedding <=> query); only status = 'approved'; HNSW index on embedding vector_cosine_ops
```

### Representative SQL
```sql
-- A patient's latest assessments (RLS adds "user_id = auth.uid()" automatically)
select score, model_version, created_at from heart_risk_assessments order by created_at desc limit 5;
-- Admin: how many chunks await review
select count(*) from medical_knowledge where status = 'pending';
```

### The full migration source
{{MIGRATION:core_schema}}
{{MIGRATION:storage}}

# Part 7 — API Documentation, Security and Privacy

## 32. API Documentation
Base path `/api`. Interactive OpenAPI UI is served by FastAPI at `/api/docs` (when the API runs). Auth = Supabase access token in `Authorization: Bearer <JWT>`; the backend verifies it with Supabase Auth, loads role/status from `profiles`, and rejects suspended accounts.

### Inventory (generated from the live OpenAPI schema)


| Method | Endpoint | Summary | Auth | Request body | Success |
|---|---|---|---|---|---|
| DELETE | `/api/account` | Delete Account | Bearer JWT | – | 204 |
| GET | `/api/account/export` | Export Account | Bearer JWT | – | 200 |
| GET | `/api/admin/audit-logs` | Audit Logs | Bearer JWT (admin) | – | 200 |
| GET | `/api/admin/evaluation` | Evaluation | Bearer JWT (admin) | – | 200 |
| GET | `/api/admin/overview` | Overview | Bearer JWT (admin) | – | 200 |
| GET | `/api/admin/users` | Users | Bearer JWT (admin) | – | 200 |
| PATCH | `/api/admin/users/{target_id}` | Update User | Bearer JWT (admin) | JSON | 200 |
| POST | `/api/chat` | Chat | Bearer JWT | JSON | 200 |
| GET | `/api/chat/suggestions` | Suggestions | none | – | 200 |
| POST | `/api/documents/analyze` | Analyze | Bearer JWT | JSON | 200 |
| POST | `/api/documents/upload` | Upload | Bearer JWT | multipart/form-data | 201 |
| DELETE | `/api/documents/{document_id}` | Delete | Bearer JWT | – | 204 |
| GET | `/api/documents/{document_id}/url` | Signed Url | Bearer JWT | – | 200 |
| GET | `/api/health` | Health | none | – | 200 |
| POST | `/api/knowledge/ingest` | Ingest | Bearer JWT (reviewer/admin) | JSON | 201 |
| POST | `/api/knowledge/{knowledge_id}/status` | Set Status | Bearer JWT (reviewer/admin) | JSON | 200 |
| GET | `/api/model-info` | Model Info | none | – | 200 |
| POST | `/api/predict` | Predict | Bearer JWT | JSON | 200 |
| POST | `/api/prescriptions/review` | Review | Bearer JWT | JSON | 200 |



`POST /internal/ocr` (OCR worker, hidden from OpenAPI, `X-Worker-Token`) is internal. The seven endpoints named in the brief are all implemented: `GET /api/health`, `GET /api/model-info`, `POST /api/predict`, `POST /api/chat`, `POST /api/documents/upload`, `POST /api/documents/analyze`, `POST /api/prescriptions/review`. Additional endpoints exist only because their functionality is implemented.

### Common error format
```json
{ "error": { "code": "validation_error", "message": "Invalid request.", "fields": [ { "field": "age", "message": "Input should be greater than or equal to 18" } ] } }
```
| HTTP | `code` | When |
|---|---|---|
| 401 | `unauthenticated`, `invalid_token` | missing/expired token |
| 403 | `forbidden`, `account_suspended`, `consent_required`, `no_profile` | role, suspension or missing AI consent |
| 404 | `document_not_found`, `conversation_not_found`, `not_found` | not found **or not yours** (RLS makes both identical) |
| 409 | `self_lockout` | admin tries to demote/suspend self |
| 422 | `validation_error`, `invalid_file`, `confirmation_required`, `empty_update` | bad input |
| 429 | `rate_limited` | per-user sliding window |
| 502 | `gemini_error`, `storage_error`, `ocr_worker_error` | upstream failure |
| 503 | `service_not_configured`, `model_missing`, `ocr_unavailable` | missing key/artifact/OCR engine, with a setup hint |
| 500 | `internal_error`, `analysis_failed`, `db_error` | unexpected (details only in server logs, exception type only) |

### GET /api/health — public
Purpose: configuration/status probe (never reveals secrets). Response (real output):
```json
{"status":"ok","services":{"supabase":{"configured":true},"gemini":{"configured":false,"model":"gemini-2.5-flash"},"ml_model":{"loaded":true,"version":"mediguide-heart-1.0.0"},"ocr":{"available_in_this_runtime":true,"worker_url_configured":false}}}
```
### GET /api/model-info — public
Returns `model_meta.json` (version, selected model, dataset facts, all metrics, library versions) plus `intended_use`. 503 `model_missing` if the artifact is absent.

### POST /api/predict — auth, 20/min
Request (all fields required; ranges enforced): 
```json
{"age":63,"sex":1,"cp":1,"trestbps":145,"chol":233,"fbs":1,"restecg":2,"thalach":150,"exang":0,"oldpeak":2.3,"slope":3,"ca":0,"thal":6}
```
Response 200 (real output, long text fields shortened):
```json
{
 "prediction": 0,
 "score": 0.1773,
 "model_version": "mediguide-heart-1.0.0",
 "model_name": "Logistic Regression",
 "assessment_id": "ff8d36a5-b83e-4190-8758-59efcadf3c9a",
 "label": "lower_risk_pattern",
 "explanation": {
  "en": "…"
 },
 "test_metrics_of_selected_model": {
  "accuracy": 0.8689,
  "precision": 0.8125,
  "recall": 0.9286,
  "f1": 0.8667,
  "roc_auc": 0.9578
 },
 "disclaimer": {
  "en": "Educational/research tool. Not a diagnosis. Consult a qualified doctor.",
  "ar": "أداة تعليمية/بحثية وليست تشخيصًا. استشر طبيبًا مختصًا."
 }
}
```
Errors: 401, 422 (field list), 503.

### POST /api/chat — auth, 15/min, `text/event-stream`
Request: `{"message":"What is LDL?","conversation_id":null,"locale":"en"}`. Events: `{"type":"meta","conversation_id":"…","emergency":false}`, optional `{"type":"sources","sources":[{"n":1,"source_name":"…","source_url":"…","published_on":null,"last_reviewed_on":"…","excerpt":"…","similarity":0.71}]}`, many `{"type":"delta","text":"…"}`, `{"type":"error","code":"…","message":"…"}`, `{"type":"done","message_id":"…"}`. Errors before streaming: 503 `service_not_configured` (no key), 403 `consent_required`, 404 foreign `conversation_id`.

### POST /api/documents/upload — auth, 10/min
`multipart/form-data`: `file` (JPG/PNG/PDF ≤ 20 MB), `doc_type` ∈ `xray|ecg|lab|prescription|general`. 201 → `{document:{id,doc_type,storage_bucket,storage_path,status:"uploaded",…}, file_info:{mime_type,size_bytes,width,height,…}}`. 422 `invalid_file` with the exact reason.

### POST /api/documents/analyze — auth, 10/min
`{"document_id":"<uuid>"}` → `{report:{id,report_type,ocr_engine,raw_text,extracted:{…},warnings:[…]}, verified:false, note:"…"}`. `extracted` by type: lab → `{report_date, results:[{test,value,unit,reference_low,reference_high,status,source_line}], warnings}`; ecg → `{measurements:{heart_rate_bpm:{value,meaning},…}}`; prescription → `{medications:[{name,name_match_score,dosage,frequency,duration,source_line,warnings}], requires_user_confirmation:true}`; xray → `{image:{…}, diagnosis_performed:false, note}`. 404 for another user's document; 503 `ocr_unavailable`.

### GET /api/documents/{id}/url and DELETE /api/documents/{id}
Signed URL valid 120 s (`{url, expires_in}`); delete removes the stored object and the row (reports cascade). Both audited.

### POST /api/prescriptions/review — auth, 20/min
Request `{"medications":[{"name":"warfarin","dosage":"5 mg","frequency":"daily"},{"name":"ibuprofen"}],"document_id":null,"user_confirmed":false,"save":false}`. Response (real output):
```json
{
 "warnings": [
  {
   "type": "missing_dosage",
   "severity": "warning",
   "message": "ibuprofen: dosage missing."
  },
  {
   "type": "missing_frequency",
   "severity": "info",
   "message": "ibuprofen: frequency missing."
  },
  {
   "type": "no_allergy_info",
   "severity": "info",
   "message": "No allergies are recorded in your profile, so no allergy check was possible."
  }
 ],
 "interactions": [
  {
   "drugs": [
    "ibuprofen",
    "warfarin"
   ],
   "severity": "major",
   "summary": "Combining an anticoagulant with antiplatelet drugs or NSAIDs can increase bleeding risk.",
   "source": {
    "name": "Warfarin prescribing information (FDA), 'Drug Interactions' section",
    "url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=warfarin"
   },
   "curated": true
  }
 ],
 "coverage_note": "Curated starter list of widely documented interaction classes. NOT exhaustive: no warning does not mean a combination is safe. Entries must be approved by a medical reviewer before any real-world use.",
 "pharmacist_notice": {
  "en": "This review is informational. It does not prescribe, stop, replace or change any medication or dose, and it cannot declare any prescription safe for you. A pharmacist or doctor must verify all medication decisions.",
  "ar": "هذه المراجعة معلوماتية فقط. لا تصف دواءً ولا توقفه ولا تستبدله ولا تغير جرعته، ولا يمكنها اعتبار أي روشتة آمنة لك. يجب أن يراجع الصيدلي أو الطبيب كل القرارات الدوائية."
 },
 "allergy_check_performed": false,
 "drug_information": [
  {
   "name": "ibuprofen",
   "status": "unavailable",
   "reason": "ProxyError",
   "source": "DailyMed (NLM)"
  },
  {
   "name": "warfarin",
   "status": "unavailable",
   "reason": "ProxyError",
   "source": "DailyMed (NLM)"
  }
 ]
}
```
(`drug_information.status:"unavailable"` here because the sandbox could not reach DailyMed.) `save:true` without `user_confirmed:true` → 422 `confirmation_required`.

### Knowledge, admin and account
`POST /api/knowledge/ingest` (reviewer/admin) `{source_name, source_url, title, text, language, published_on?, last_reviewed_on?}` → `{chunks_created, status:"pending"}`. `POST /api/knowledge/{id}/status` `{status}`. `GET /api/admin/overview|users|audit-logs|evaluation`, `PATCH /api/admin/users/{id}` `{role?,status?}` (admin). `GET /api/account/export`, `DELETE /api/account` (self).

## 33. Security and Privacy
| Control | Implementation | Verified by |
|---|---|---|
| Authentication | Supabase Auth, email confirmation, password ≥ 8 with letters+digits, refresh-token rotation | E2E registration/login |
| Server-side authorisation | `get_current_user`, role guards, suspended check on **every** request | `test_admin_endpoints_forbidden_for_patients`, suspension test |
| RLS | Every table; owner-only for medical rows; admin has **no** read policy on them | `test_rls_*`, `test_admin_cannot_read_patient_private_data` |
| Anti-escalation | Trigger blocks role/status self-change; no INSERT/DELETE policy on `profiles` | `test_user_cannot_escalate_role` |
| Cross-tenant linking | `assert_same_owner` triggers | `test_cannot_attach_message_to_foreign_conversation` |
| Private storage | 5 private buckets, `<uid>/…` path policy, MIME allow-list, 20 MiB limit | upload tests, direct-storage access test |
| Signed URLs | 120 s | upload/view test |
| Safe uploads | magic bytes, extension, size, decode, pixel & page limits, sanitised names | `test_unit.py` validation tests |
| Secrets | `.env.local` git-ignored; service-role key only in backend; `.env.example` has placeholders | code review (no `NEXT_PUBLIC_` secret) |
| Rate limiting | per-user sliding window | `test_rate_limit` (per-instance only) |
| Logging | exception type only; audit metadata has no medical text | code review |
| Consent | terms at registration; separate AI-processing consent before chat | `test_chat_requires_consent` |
| Erasure & portability | `DELETE /api/account` removes files then auth user (rows cascade); JSON export | integration + E2E |
| Headers | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` | config |
| XSS | Markdown rendered without raw HTML | design (`react-markdown`) |
| Prompt injection | sources treated as untrusted data in the prompt | design (not adversarially tested) |
| Open redirect | `next` parameter must start with `/` and not `//` | code review |

**Known gaps (honest list).** CSP header not set; rate limiter is per-instance; audit log is written by the app (not DB triggers); no MFA; no malware scanning of uploads; retention policy exists as a *setting* (`retention_days_documents`) but **no job enforces it** (Planned); cookie/session settings are Supabase defaults; no penetration test or independent security review was done; RLS tests cover the main tables, not exhaustively every column of every table.

**Egyptian regulatory context (summary, not legal advice).** Egypt's **Personal Data Protection Law No. 151 of 2020** requires a lawful basis (typically explicit consent), purpose limitation, data minimisation, security, and special care for *sensitive/health data*; cross-border transfer rules and licensing from the Personal Data Protection Center apply. Medical software and AI used for diagnosis is regulated by the **Egyptian Drug Authority (EDA)** (medical-device/software rules) and health professions by the Ministry of Health; MediGuide AI avoids a diagnostic claim precisely to stay an educational tool. Sending chat text to Google Gemini is a cross-border processing activity → requires the explicit consent already implemented plus a data-processing agreement and, likely, regulator guidance. **These obligations must be confirmed by a qualified Egyptian lawyer before any real deployment**; development must use synthetic or authorised de-identified data only (all screenshots/tests here use synthetic data).

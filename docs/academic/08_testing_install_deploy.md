# Part 8 — Testing, Installation and Deployment

## 34. Testing and Quality Assurance
**Rule:** nothing below is claimed unless it was executed. Results are from this repository on 2026-11-22 against a real local Supabase stack (Postgres 17, GoTrue, Storage, Mailpit) started with `npx supabase start`.

| Suite | Command | Files / tests | Result |
|---|---|---|---|
| Backend unit, ML, integration, security | `python -m pytest tests/backend` | `test_unit.py` 25, `test_ml.py` 5, `test_integration.py` 29 = **59** | **59 passed** (Tesseract installed) |
| Same, in a clean venv with only `requirements.txt` (Vercel-like: no OpenCV/Tesseract) | `…/vercel-venv/bin/python -m pytest tests/backend` | 59 | **56 passed, 3 skipped** (the 3 OCR-engine tests need Tesseract; a separate test proves the clear 503 `ocr_unavailable`) |
| End-to-end (Playwright 1.63, real Chromium, real app + API + Supabase) | `npx playwright test` | 16 (15 desktop + 1 mobile viewport) | **16 passed** |
| Type check + production build | `npm run build` | – | **passed** (Next.js 16.4.6, Turbopack, TypeScript) |
| Lint | `npx eslint .` | – | **0 errors, 11 warnings** (`any` in OCR-payload typing; two rules relaxed in `eslint.config.mjs` with comments) |

**What the tests cover (by brief category)**
- *Unit:* emergency detection (EN/AR positives and negatives), chunking, HTML cleaning, file validation (extension mismatch, fake executable, oversize, truncated PNG, DICOM, traversal), parsers (lab/ECG/prescription), medication rules.
- *ML pipeline:* artifacts exist; report matches dataset (303 rows, split sums, confusion matrices sum to 61); selection rule documented as training-split based; dataset hash matches; prediction shape; missing-value handling.
- *API/auth/authz:* 401 on missing/invalid token; admin routes 403 for patients; suspended users 403; self-lockout 409; validation 422 without echoing values; no stack traces.
- *RLS isolation:* Bob cannot read, insert for, update, delete or attach to Alice's rows; admin cannot read Alice's private rows; anonymous key sees nothing; Bob cannot analyse/sign/delete Alice's document nor fetch it from storage; public bucket URL fails; patients cannot read pending knowledge.
- *Upload/OCR:* real PNG rendered with text → upload → Tesseract → "Total Cholesterol 245 … high"; ECG numbers; X-ray never diagnoses; OCR worker token protection and API→worker delegation; signed URL works; delete removes file and rows.
- *AI integration & RAG:* with the Gemini SDK replaced by a **test double** (clearly labelled in the test file): consent gate, streaming + persistence, emergency warning first with 123, approved-only retrieval with source attribution, missing key → 503.
- *Missing keys / unavailable services:* no Gemini key (503), no OCR (503), DailyMed unreachable (status `unavailable`).
- *E2E:* Arabic RTL default, English LTR persisted via cookie, dark mode persisted, protected-route redirect, **registration → real verification e-mail read from Mailpit → login → logout**, unverified login rejected, wrong password, password-recovery e-mail sent, risk form validation + result, document upload with preview → OCR → signed URL → delete, fake image rejected, medication review/confirm/save, chat consent + not-configured message, profile persistence, patient blocked from admin, admin tabs, account deletion, mobile layout without horizontal overflow.

**Not tested / limitations of testing.** Real Gemini responses and embedding quality; real DailyMed; Vercel runtime itself; browsers other than Chromium; accessibility audit tooling; load/performance; adversarial prompt-injection; handwritten or photographed (noisy) documents; Arabic OCR accuracy (Arabic language data is installed but no Arabic document test exists).

## 35. Installation Guide (local development)
Prerequisites: Node 22+, Python 3.12, Docker (for Supabase), Tesseract + Arabic data (`sudo apt install tesseract-ocr tesseract-ocr-ara poppler-utils`), `uv` (or `pip`).
```bash
git clone <repo> && cd mediguide-ai
npm install                                   # frontend deps
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements-dev.txt        # backend + OCR + test deps
npx supabase start                            # local Postgres/Auth/Storage; prints URL and keys
npx supabase db reset                         # applies supabase/migrations/*
cp .env.example .env.local                    # then fill values printed by `supabase start`
python -m ml.train                            # (optional) retrain; artifacts are already committed
uvicorn backend.app.main:app --port 8000      # API
npm run dev                                   # app on http://localhost:3000 (proxies /api to :8000)
```
Create the first administrator (SQL against your database): `update profiles set role='admin' where id='<user uuid>';` (the UI cannot self-promote). Set `GEMINI_API_KEY` to enable chat, then ingest and approve knowledge in **Admin → Knowledge base**.

Tests: `python -m pytest tests/backend` and, with `npm run build && npm start` plus the API running, `npx playwright test`.

## 36. Deployment Guide
**Current status: prepared, NOT deployed** (no Vercel, hosted-Supabase or GitHub credentials were available).

1. **Supabase (managed):** create a project; `npx supabase link --project-ref <ref>`; `npx supabase db push`. Enable email confirmations (`auth.email.enable_confirmations`), set Site URL and redirect URLs to the Vercel domain, configure a real SMTP provider (the default sender is rate-limited). Ensure the `vector` extension is enabled.
2. **GitHub → Vercel:** push the repo; import in Vercel (framework: Next.js). `vercel.json` rewrites `/api/*` to the Python function `api/index.py`, bundles `backend/app`, `backend/data`, `ml/features.py` and `ml/artifacts/**` (excluding the raw dataset/reports) and sets `maxDuration` 60 s. `.python-version` pins 3.12; root `requirements.txt` is what Vercel installs (identical to `backend/requirements.txt`, enforced by a test).
3. **Environment variables (Vercel → Settings):** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (server only), `GEMINI_API_KEY`, `ALLOWED_ORIGINS`, optionally `OCR_WORKER_URL` + `OCR_WORKER_TOKEN`. Do **not** set `API_DEV_ORIGIN` in production.
4. **OCR worker:** `docker build -f Dockerfile.ocr -t mediguide-ocr .` and run it on any container host with `OCR_WORKER_TOKEN`; expose HTTPS. Without it, OCR of images returns a clear 503 (digital-text PDFs still work).
5. **Never retrain on deploy:** the model artifact is in git; `ml/train.py` is a developer tool.

**What was verified about deployability:** a clean Python 3.12 environment built only from `requirements.txt` imports the app and passes the tests (56 passed, 3 OCR-engine tests skipped); installed size is **325 MB** (scipy 81 MB, pandas 45 MB, sklearn 32 MB…), below Vercel's documented Python bundle limit as understood at writing — **confirm the current limit on vercel.com/docs**. The Vercel function runtime, the rewrite configuration and cold-start time have **not** been tested on Vercel. Serverless caveats: the in-memory rate limiter is per instance; no local-disk writes are used; long OCR belongs on the worker.

# Part 3 — Frontend, Backend and Libraries

## 20. Frontend Documentation
**Stack:** Next.js 16.4 App Router, React 19, TypeScript (strict), Tailwind CSS 4 (tokens in `app/globals.css`), shadcn/ui-*style* primitives (`components/ui/index.tsx`, hand-written because the shadcn registry was unreachable; same cva + Radix `Slot` + `cn()` pattern), Lucide icons, Recharts, React Hook Form + Zod.

> Next.js 16 differs from older versions: the former `middleware.ts` is now **`proxy.ts`**, and cookies/headers are async. The project reads the bundled docs (`node_modules/next/dist/docs`) as `AGENTS.md` requires. Cache Components were *not* enabled (every page is per-user and dynamic).

### Brand and design system
Primary `#1677E8`, cyan `#16C5D5`, navy `#102A56`, white/soft-blue backgrounds, rounded cards (`--radius-card: 1.25rem`), gradient buttons, subtle float/pulse animations (disabled under `prefers-reduced-motion`). The heart-and-pulse logo is an original inline SVG (`components/logo.tsx`, `public/icon.svg`). No external fonts (system Arabic-capable font stack) so builds work offline.

### Internationalisation
`lib/i18n/dict.ts` holds ~230 keys in `ar` and `en` (TypeScript enforces that both have identical keys). The `locale` cookie is read in `app/layout.tsx` (server) to set `<html lang dir>`, so Arabic RTL renders on first paint; `Providers` switches language and writes the cookie. Layout uses logical properties (`ps-`, `me-`, `border-e`) so RTL/LTR mirror automatically. Dark mode: a `dark` class set before hydration by an inline script (no flash).

### Pages and modules
| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Landing: hero, features, disclaimer |
| `/login`, `/register`, `/forgot-password`, `/reset-password` | `app/(auth)/*` | Auth forms (RHF + Zod) |
| `/auth/callback` | `app/auth/callback/route.ts` | Exchanges the email-link code for a session; guards open redirects |
| `/app` | `app/app/page.tsx` | Dashboard: counts + merged medical timeline |
| `/app/chat` | `app/app/chat/page.tsx` | Streaming chat (SSE reader), history, consent gate, sources, copy/delete |
| `/app/risk` | `app/app/risk/page.tsx` | 13-field form, result, metrics chart, limitations, history |
| `/app/documents` | `app/app/documents/page.tsx` | Upload (XHR progress, preview), table, analyze, signed-URL view, delete, report |
| `/app/medications` | `app/app/medications/page.tsx` | OCR import/manual entry, safety review, confirm + save |
| `/app/profile` | `app/app/profile/page.tsx` | Profile, medical profile, language, export, delete account |
| `/app/admin` | `app/app/admin/page.tsx` | Tabs: system, users, knowledge, evaluation, audit (role-gated) |
| `proxy.ts` | – | Refreshes session cookie; redirects unauthenticated `/app/*` to `/login?next=` |

### How the frontend talks to the backend
`lib/api.ts` reads the Supabase session, adds `Authorization: Bearer <access_token>`, calls `/api/*` (same origin; `next.config.ts` rewrites to FastAPI in development, `vercel.json` routes to the Python function in production) and converts the structured error `{error:{code,message,fields}}` into an `ApiError`. Uploads use `XMLHttpRequest` because `fetch` cannot report upload progress. Chat reads the response body as a stream and parses `data: {...}` SSE events.

### Accessibility and safety in the UI
`role="alert"` on errors, `aria-current` on navigation, `aria-live` chat log, visible focus ring, emergency banner for emergency answers, a persistent disclaimer footer on every app page, OCR results always labelled "not verified".

## 21. Backend Documentation
`backend/app/` (FastAPI, Python 3.12):
| Module | Responsibility |
|---|---|
| `main.py` | App factory; CORS allow-list; security headers; structured error handlers (validation errors never echo input values; unhandled errors log only the exception type) |
| `config.py` | `Settings` from environment (no secrets in code) |
| `auth.py` | `get_current_user`: validates the bearer token with Supabase Auth (`auth.get_user`), loads role/status/consent from `profiles`; suspended → 403; role guards `AdminUser`, `ReviewerUser` |
| `db.py` | `user_client(token)` (RLS applies) and `service_client()` (server-only) |
| `ratelimit.py` | Sliding-window limiter (per instance; documented limitation on serverless) |
| `audit.py` | Writes `audit_logs`, never medical content |
| `schemas.py` | Pydantic models, incl. `HeartInput` with clinical ranges |
| `routers/health.py` | `/api/health`, `/api/model-info` |
| `routers/predict.py` | `/api/predict` |
| `routers/chat.py` | `/api/chat` (SSE), `/api/chat/suggestions` |
| `routers/documents.py` | upload, analyze, signed URL, delete |
| `routers/prescriptions.py` | `/api/prescriptions/review` |
| `routers/admin.py` | knowledge ingest/status, admin overview/users/audit/evaluation, account delete/export |
| `routers/ocr_worker.py` | Internal `/internal/ocr` for the Docker worker (token-protected) |
| `services/safety.py` | Emergency regex, system prompt, suggested questions |
| `services/gemini.py` | Embeddings and streaming generation |
| `services/rag.py` | clean, chunk, ingest, retrieve, attribute |
| `services/ml_service.py` | Load joblib pipeline once; predict |
| `services/drugs.py` | Medication review rules and DailyMed lookup |
| `ocr/validate.py`, `engine.py`, `parsers.py` | File validation, OCR, text→structure |
| `../data/*.json` | Drug-name lexicon (no drug facts) and curated interaction rules |
`api/index.py` is the Vercel entry point that imports the same `app`.

## 22. Python Libraries and Their Functions — verified inventory
**Method (Rule 1).** `scripts_inventory.py` parses every `import` in `backend/`, `ml/`, `api/` with Python's `ast` module and every import/require in the TypeScript sources, then matches them against `requirements*.txt` and `package-lock.json` versions. The table below is generated from that result; "Modules using it" are the files where the import was found. Versions are the **installed** versions.

{{LIB_TABLE}}

**Practical example (end to end for one library — scikit-learn + joblib):** training builds `Pipeline([("prep", ColumnTransformer(...)), ("clf", LogisticRegression())])`, `GridSearchCV` tunes it on the training split, `joblib.dump` stores the whole pipeline, and at request time `ml_service.load_model()` unpickles it once and calls `predict_proba(pd.DataFrame([row]))`. Preprocessing is inside the pipeline, so training and serving can never disagree.

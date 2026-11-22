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



### Python dependencies

| Library | Version | Purpose | Why selected | Modules using it | Example |
|---|---|---|---|---|---|
| **fastapi** | 0.165.0 | HTTP API framework | Typed routes, automatic validation/OpenAPI, async streaming (SSE), runs on Vercel | `backend/app/auth.py`, `backend/app/errors.py`, `backend/app/main.py` | `@router.post('/predict')\ndef predict(body: HeartInput, user: User): ...` |
| **google-genai** | 3.6.1 | Official Gemini SDK | Embeddings and streaming generation, called server-side only | `backend/app/services/gemini.py` | `client.models.generate_content_stream(model=..., contents=...)` |
| **httpx** | 0.28.1 | HTTP client | DailyMed lookup and API-to-OCR-worker calls with timeouts | `backend/app/ocr/engine.py`, `backend/app/services/drugs.py` | `httpx.get(url, params=..., timeout=10)` |
| **joblib** | 1.6.0 | Model persistence | Saves/loads the fitted pipeline (preprocessing + model together) | `backend/app/services/ml_service.py`, `ml/train.py` | `joblib.dump(final, 'heart_model.joblib', compress=3)` |
| **matplotlib** | 3.11.2 | Charts | Generates the real ROC/confusion/comparison PNGs from results | `ml/train.py` | `fig.savefig('roc_curves.png')` |
| **numpy** | 2.5.5 | Numeric arrays | Direct use in training charts and OpenCV image decoding; also required by scikit-learn | `backend/app/ocr/engine.py`, `ml/train.py` | `np.frombuffer(data, np.uint8)` |
| **opencv-python-headless** | 5.1.0.95 | Image pre-processing for OCR | Grayscale, upscale, denoise, adaptive threshold improve Tesseract accuracy | `backend/app/ocr/engine.py` | `cv2.adaptiveThreshold(img, 255, ...)` |
| **pandas** | 3.1.1 | Tabular data | Loads the dataset; builds the one-row DataFrame the pipeline expects | `backend/app/services/ml_service.py`, `ml/train.py` | `pd.read_csv(DATA, header=None, names=COLUMNS, na_values='?')` |
| **pillow** | 13.0.0 | Image decoding/validation | Verifies uploads are real images, reads metadata, bomb protection | `backend/app/ocr/validate.py`, `backend/app/routers/documents.py` | `Image.open(io.BytesIO(data)).verify()` |
| **pydantic** | 2.14.4 | Request/response validation models | Rejects invalid medical inputs before any logic runs | `backend/app/schemas.py` | `age: int = Field(ge=18, le=100)` |
| **pydantic-settings** | 2.16.3 | Typed environment configuration | Secrets only from env vars, never hard-coded | `backend/app/config.py` | `class Settings(BaseSettings): gemini_api_key: str = ''` |
| **pypdf** | 7.1.1 | PDF reading | Validates PDFs and extracts the text layer of digital reports | `backend/app/ocr/engine.py`, `backend/app/ocr/validate.py` | `PdfReader(io.BytesIO(data)).pages[0].extract_text()` |
| **pytesseract** | 0.3.13 | Python wrapper for the Tesseract OCR binary | Real OCR with per-word confidence, Arabic + English | `backend/app/ocr/engine.py` | `pytesseract.image_to_data(img, lang='eng+ara', output_type=Output.DICT)` |
| **pytest** | 9.2.0 | Test runner | Unit, integration, security and ML tests | tests/backend/* | `python -m pytest tests/backend` |
| **python-multipart** | 0.0.34 | Multipart parser (IMPLICIT) | Required by FastAPI for `UploadFile`/`Form`; never imported by our code | routers/documents.py (indirect) | n/a |
| **scikit-learn** | 1.9.1 | Machine learning | Pipelines, GridSearchCV and the 4 required algorithms in one consistent API | `ml/train.py` | `Pipeline([('prep', preprocessor()), ('clf', LogisticRegression())])` |
| **supabase** | 2.34.1 | Supabase Python client (PostgREST, Auth, Storage) | Calls Postgres as the user (RLS enforced) and storage with the user's JWT | `backend/app/db.py` | `user_client(token).table('messages').select('*')` |
| **uvicorn** | 0.54.0 | ASGI server (RUNTIME TOOL) | Runs the API locally/in Docker; not imported; Vercel supplies its own server | Dockerfile.ocr, local dev command | `uvicorn backend.app.main:app` |

### JavaScript/TypeScript dependencies

| Library | Version | Purpose | Why selected | Modules using it | Example |
|---|---|---|---|---|---|
| **@hookform/resolvers** | 7.0.8 | Connects Zod to React Hook Form | Single source of validation rules per form | `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx`, `app/app/risk/page.tsx` | `resolver: zodResolver(schema)` |
| **@supabase/ssr** | 0.12.7 | Supabase auth for Next.js (cookie sessions) | Browser, server and proxy clients share one cookie session | `lib/supabase/client.ts`, `lib/supabase/server.ts`, `proxy.ts` | `createBrowserClient(url, key)` |
| **@supabase/supabase-js** | 2.119.2 | Supabase JS SDK (PEER DEPENDENCY) | Peer dependency of @supabase/ssr; not imported directly | (via @supabase/ssr) | n/a |
| **class-variance-authority** | 0.7.1 | Variant styling | shadcn-style Button variants | `components/ui/index.tsx` | `cva('inline-flex', {variants: {...}})` |
| **clsx** | 2.1.1 | Conditional class names | Used by `cn()` | `lib/utils.ts` | `clsx('a', cond && 'b')` |
| **lucide-react** | 1.77.0 | Icons | Clean medical icons | `app/app/chat/page.tsx`, `app/app/documents/page.tsx`, `app/app/medications/page.tsx` | `<Activity size={18} />` |
| **next** | 16.4.6 | React framework (App Router) | SSR layouts, proxy.ts route guard, route handlers, Vercel-native | `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx`, `app/(auth)/reset-password/page.tsx` | `export default async function RootLayout()` |
| **radix-ui** | 1.8.1 | Accessible primitives | `Slot` powers `Button asChild` (only primitive used) | `components/ui/index.tsx` | `<Button asChild><Link/></Button>` |
| **react** | 19.3.0 | UI library | Component model for every page | `app/(auth)/forgot-password/page.tsx`, `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx` | `const [busy, setBusy] = useState(false)` |
| **react-dom** | 19.3.0 | React DOM renderer (IMPLICIT) | Required by Next.js, never imported by our code | (framework) | n/a |
| **react-hook-form** | 7.92.0 | Form state | Login/register/risk forms with minimal re-renders | `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx`, `app/app/risk/page.tsx` | `const {register, handleSubmit} = useForm()` |
| **react-markdown** | 10.1.0 | Safe Markdown rendering | Renders assistant answers without raw HTML | `app/app/chat/page.tsx` | `<ReactMarkdown remarkPlugins={[remarkGfm]}>` |
| **recharts** | 3.11.0 | Charts | Model-metric bar charts (risk result, admin evaluation) | `app/app/admin/page.tsx`, `app/app/risk/page.tsx` | `<BarChart data={...}><Bar dataKey='v'/></BarChart>` |
| **remark-gfm** | 4.0.1 | GitHub-flavoured Markdown (tables, lists) | Tables/lists in answers | `app/app/chat/page.tsx` | see above |
| **tailwind-merge** | 3.7.1 | Resolves conflicting Tailwind classes | Used by `cn()` | `lib/utils.ts` | `twMerge('p-2', 'p-4')` |
| **zod** | 4.6.7 | Schema validation | Same constraints as the backend, shown inline | `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx`, `app/app/risk/page.tsx` | `z.coerce.number().min(18).max(100)` |
| **@playwright/test** | 1.63.0 | End-to-end browser tests | Real Chromium against the real stack | `playwright.config.ts`, `tests/e2e/helpers.ts`, `tests/e2e/i18n-auth.spec.ts` | `await page.goto('/login')` |
| **@tailwindcss/turbopack** | 4.3.3 | Tailwind loader for Turbopack (TOOLCHAIN) | Generated by create-next-app; referenced in next.config.ts | `next.config.ts` | n/a |
| **@types/node** | 20.19.43 | Node typings (TOOLCHAIN) | Types only | (compiler) | n/a |
| **@types/react** | 19.3.0 | React typings (TOOLCHAIN) | Types only | (compiler) | n/a |
| **@types/react-dom** | 19.3.0 | React DOM typings (TOOLCHAIN) | Types only | (compiler) | n/a |
| **eslint** | 9.39.5 | Linter | Static quality gate | `eslint.config.mjs` | `npx eslint .` |
| **eslint-config-next** | 16.4.6 | Next.js lint rules | Core-web-vitals + TypeScript rules | `eslint.config.mjs` | n/a |
| **tailwindcss** | 4.3.3 | Utility CSS (TOOLCHAIN) | Imported via `@import "tailwindcss"` in globals.css; design tokens in `@theme` | app/globals.css | `className="rounded-card p-5"` |
| **typescript** | 5.9.3 | Type system (TOOLCHAIN) | Strict typing; checked by `next build` | tsconfig.json | n/a |

### Dependencies that are installed but not imported by application code

| Library | Version | Classification |
|---|---|---|
| pytest | 9.2.0 | Test runner |
| python-multipart | 0.0.34 | Multipart parser (IMPLICIT) |
| uvicorn | 0.54.0 | ASGI server (RUNTIME TOOL) |
| @supabase/supabase-js | 2.119.2 | Supabase JS SDK (PEER DEPENDENCY) |
| react-dom | 19.3.0 | React DOM renderer (IMPLICIT) |
| @types/node | 20.19.43 | Node typings (TOOLCHAIN) |
| @types/react | 19.3.0 | React typings (TOOLCHAIN) |
| @types/react-dom | 19.3.0 | React DOM typings (TOOLCHAIN) |
| tailwindcss | 4.3.3 | Utility CSS (TOOLCHAIN) |
| typescript | 5.9.3 | Type system (TOOLCHAIN) |

None of these is an *unnecessary* dependency: each is an implicit runtime requirement, peer dependency, toolchain package or CLI tool (pytest is exercised by the test suite, which is outside the scanned source folders). Libraries named in the original brief but **not installed** and therefore **not documented as implemented**: PaddleOCR, shadcn/ui CLI components (a shadcn-*style* component set was hand-written instead), Scikit-image, pdfplumber, DICOM tooling (pydicom), Tesseract language packs other than eng/ara.

Transitive Python dependency worth knowing: `PyJWT` is required by `supabase-auth` and is installed automatically, but our code does not import it (tokens are verified by Supabase Auth, not decoded locally).



**Practical example (end to end for one library — scikit-learn + joblib):** training builds `Pipeline([("prep", ColumnTransformer(...)), ("clf", LogisticRegression())])`, `GridSearchCV` tunes it on the training split, `joblib.dump` stores the whole pipeline, and at request time `ml_service.load_model()` unpickles it once and calls `predict_proba(pd.DataFrame([row]))`. Preprocessing is inside the pipeline, so training and serving can never disagree.

"""Builds docs/academic/*.md from hand-written templates (docs/src/*.md) + REAL data:
dependency inventory (scripts_inventory.py), ML evaluation JSON, OpenAPI schema, PostgreSQL catalog, Mermaid sources."""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SRC, OUT = ROOT / "docs" / "src", ROOT / "docs" / "academic"
OUT.mkdir(exist_ok=True)

def psql(q):
    r = subprocess.run(["psql", "postgresql://postgres:postgres@127.0.0.1:54322/postgres", "-At", "-F", "|", "-c", q], capture_output=True, text=True, check=True)
    return [l.split("|") for l in r.stdout.strip().splitlines() if l]

# ---------------- library inventory
LIB = {  # name: (purpose, why, module, example)
 "fastapi": ("HTTP API framework", "Typed routes, automatic validation/OpenAPI, async streaming (SSE), runs on Vercel", "backend/app/main.py, routers/*", "`@router.post('/predict')\\ndef predict(body: HeartInput, user: User): ...`"),
 "pydantic": ("Request/response validation models", "Rejects invalid medical inputs before any logic runs", "backend/app/schemas.py", "`age: int = Field(ge=18, le=100)`"),
 "pydantic-settings": ("Typed environment configuration", "Secrets only from env vars, never hard-coded", "backend/app/config.py", "`class Settings(BaseSettings): gemini_api_key: str = ''`"),
 "httpx": ("HTTP client", "DailyMed lookup and API-to-OCR-worker calls with timeouts", "services/drugs.py, ocr/engine.py", "`httpx.get(url, params=..., timeout=10)`"),
 "supabase": ("Supabase Python client (PostgREST, Auth, Storage)", "Calls Postgres as the user (RLS enforced) and storage with the user's JWT", "backend/app/db.py and all routers", "`user_client(token).table('messages').select('*')`"),
 "google-genai": ("Official Gemini SDK", "Embeddings and streaming generation, called server-side only", "services/gemini.py", "`client.models.generate_content_stream(model=..., contents=...)`"),
 "scikit-learn": ("Machine learning", "Pipelines, GridSearchCV and the 4 required algorithms in one consistent API", "ml/train.py (and model unpickling in ml_service)", "`Pipeline([('prep', preprocessor()), ('clf', LogisticRegression())])`"),
 "pandas": ("Tabular data", "Loads the dataset; builds the one-row DataFrame the pipeline expects", "ml/train.py, services/ml_service.py", "`pd.read_csv(DATA, header=None, names=COLUMNS, na_values='?')`"),
 "numpy": ("Numeric arrays", "Direct use in training charts and OpenCV image decoding; also required by scikit-learn", "ml/train.py, ocr/engine.py", "`np.frombuffer(data, np.uint8)`"),
 "joblib": ("Model persistence", "Saves/loads the fitted pipeline (preprocessing + model together)", "ml/train.py, services/ml_service.py", "`joblib.dump(final, 'heart_model.joblib', compress=3)`"),
 "pillow": ("Image decoding/validation", "Verifies uploads are real images, reads metadata, bomb protection", "ocr/validate.py, routers/documents.py", "`Image.open(io.BytesIO(data)).verify()`"),
 "pypdf": ("PDF reading", "Validates PDFs and extracts the text layer of digital reports", "ocr/validate.py, ocr/engine.py", "`PdfReader(io.BytesIO(data)).pages[0].extract_text()`"),
 "opencv-python-headless": ("Image pre-processing for OCR", "Grayscale, upscale, denoise, adaptive threshold improve Tesseract accuracy", "ocr/engine.py (OCR worker only)", "`cv2.adaptiveThreshold(img, 255, ...)`"),
 "pytesseract": ("Python wrapper for the Tesseract OCR binary", "Real OCR with per-word confidence, Arabic + English", "ocr/engine.py (OCR worker only)", "`pytesseract.image_to_data(img, lang='eng+ara', output_type=Output.DICT)`"),
 "matplotlib": ("Charts", "Generates the real ROC/confusion/comparison PNGs from results", "ml/train.py (dev only)", "`fig.savefig('roc_curves.png')`"),
 "pytest": ("Test runner", "Unit, integration, security and ML tests", "tests/backend/*", "`python -m pytest tests/backend`"),
 "python-multipart": ("Multipart parser (IMPLICIT)", "Required by FastAPI for `UploadFile`/`Form`; never imported by our code", "routers/documents.py (indirect)", "n/a"),
 "uvicorn": ("ASGI server (RUNTIME TOOL)", "Runs the API locally/in Docker; not imported; Vercel supplies its own server", "Dockerfile.ocr, local dev command", "`uvicorn backend.app.main:app`"),
 "next": ("React framework (App Router)", "SSR layouts, proxy.ts route guard, route handlers, Vercel-native", "app/*, proxy.ts, next.config.ts", "`export default async function RootLayout()`"),
 "react": ("UI library", "Component model for every page", "app/*, components/*", "`const [busy, setBusy] = useState(false)`"),
 "react-dom": ("React DOM renderer (IMPLICIT)", "Required by Next.js, never imported by our code", "(framework)", "n/a"),
 "@supabase/ssr": ("Supabase auth for Next.js (cookie sessions)", "Browser, server and proxy clients share one cookie session", "lib/supabase/*, proxy.ts", "`createBrowserClient(url, key)`"),
 "@supabase/supabase-js": ("Supabase JS SDK (PEER DEPENDENCY)", "Peer dependency of @supabase/ssr; not imported directly", "(via @supabase/ssr)", "n/a"),
 "tailwindcss": ("Utility CSS (TOOLCHAIN)", "Imported via `@import \"tailwindcss\"` in globals.css; design tokens in `@theme`", "app/globals.css", "`className=\"rounded-card p-5\"`"),
 "@tailwindcss/turbopack": ("Tailwind loader for Turbopack (TOOLCHAIN)", "Generated by create-next-app; referenced in next.config.ts", "next.config.ts", "n/a"),
 "class-variance-authority": ("Variant styling", "shadcn-style Button variants", "components/ui/index.tsx", "`cva('inline-flex', {variants: {...}})`"),
 "clsx": ("Conditional class names", "Used by `cn()`", "lib/utils.ts", "`clsx('a', cond && 'b')`"),
 "tailwind-merge": ("Resolves conflicting Tailwind classes", "Used by `cn()`", "lib/utils.ts", "`twMerge('p-2', 'p-4')`"),
 "radix-ui": ("Accessible primitives", "`Slot` powers `Button asChild` (only primitive used)", "components/ui/index.tsx", "`<Button asChild><Link/></Button>`"),
 "lucide-react": ("Icons", "Clean medical icons", "components/*, app/app/*", "`<Activity size={18} />`"),
 "recharts": ("Charts", "Model-metric bar charts (risk result, admin evaluation)", "app/app/risk, app/app/admin", "`<BarChart data={...}><Bar dataKey='v'/></BarChart>`"),
 "react-hook-form": ("Form state", "Login/register/risk forms with minimal re-renders", "app/(auth)/*, app/app/risk", "`const {register, handleSubmit} = useForm()`"),
 "zod": ("Schema validation", "Same constraints as the backend, shown inline", "app/(auth)/*, app/app/risk", "`z.coerce.number().min(18).max(100)`"),
 "@hookform/resolvers": ("Connects Zod to React Hook Form", "Single source of validation rules per form", "app/(auth)/*, app/app/risk", "`resolver: zodResolver(schema)`"),
 "react-markdown": ("Safe Markdown rendering", "Renders assistant answers without raw HTML", "app/app/chat/page.tsx", "`<ReactMarkdown remarkPlugins={[remarkGfm]}>`"),
 "remark-gfm": ("GitHub-flavoured Markdown (tables, lists)", "Tables/lists in answers", "app/app/chat/page.tsx", "see above"),
 "@playwright/test": ("End-to-end browser tests", "Real Chromium against the real stack", "tests/e2e/*, playwright.config.ts", "`await page.goto('/login')`"),
 "eslint": ("Linter", "Static quality gate", "eslint.config.mjs", "`npx eslint .`"),
 "eslint-config-next": ("Next.js lint rules", "Core-web-vitals + TypeScript rules", "eslint.config.mjs", "n/a"),
 "typescript": ("Type system (TOOLCHAIN)", "Strict typing; checked by `next build`", "tsconfig.json", "n/a"),
 "@types/node": ("Node typings (TOOLCHAIN)", "Types only", "(compiler)", "n/a"), "@types/react": ("React typings (TOOLCHAIN)", "Types only", "(compiler)", "n/a"), "@types/react-dom": ("React DOM typings (TOOLCHAIN)", "Types only", "(compiler)", "n/a"),
}
inv = json.loads((ROOT / "docs_inventory.json").read_text())
def lib_table():
    out = []
    for eco, key in (("Python", "python"), ("JavaScript/TypeScript", "npm")):
        out += [f"### {eco} dependencies", "", "| Library | Version | Purpose | Why selected | Modules using it | Example |", "|---|---|---|---|---|---|"]
        for name, v in inv[key].items():
            p = LIB.get(name, ("?", "?", "?", "?"))
            used = ", ".join(f"`{f}`" for f in v["used_in"][:3]) or p[2]
            out.append(f"| **{name}** | {v['version']} | {p[0]} | {p[1]} | {used} | {p[3]} |")
        out.append("")
    out += ["### Dependencies that are installed but not imported by application code", ""]
    rows = [(k, v["version"], LIB[k][0]) for e in ("python", "npm") for k, v in inv[e].items() if not v["used_in"]]
    out += ["| Library | Version | Classification |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in rows]
    out += ["", "None of these is an *unnecessary* dependency: each is an implicit runtime requirement, peer dependency, toolchain package or CLI tool (pytest is exercised by the test suite, which is outside the scanned source folders). Libraries named in the original brief but **not installed** and therefore **not documented as implemented**: PaddleOCR, shadcn/ui CLI components (a shadcn-*style* component set was hand-written instead), Scikit-image, pdfplumber, DICOM tooling (pydicom), Tesseract language packs other than eng/ara.", "",
            "Transitive Python dependency worth knowing: `PyJWT` is required by `supabase-auth` and is installed automatically, but our code does not import it (tokens are verified by Supabase Auth, not decoded locally)."]
    return "\n".join(out)

# ---------------- ML
ev = json.loads((ROOT / "ml/reports/evaluation.json").read_text())
def ml_table():
    rows = ["| Model | Best hyper-parameters (CV on train only) | CV ROC-AUC (train) | Accuracy | Precision | Recall | F1 | ROC-AUC (test) | TN | FP | FN | TP |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in ev["results"].items():
        t, c = r["test"], r["confusion_matrix"]
        rows.append(f"| {n} | `{json.dumps(r['best_params'])}` | {r['cv_roc_auc_mean_train_only']} | {t['accuracy']} | {t['precision']} | {t['recall']} | {t['f1']} | {t['roc_auc']} | {c['tn']} | {c['fp']} | {c['fn']} | {c['tp']} |")
    d = ev["dataset"]
    rows += ["", f"**Dataset facts (from `ml/reports/evaluation.json`):** {d['rows']} rows ({d['positive']} disease / {d['negative']} no disease), missing values {d['missing_values']}, split {d['split']} → {d['train_rows']} train / {d['test_rows']} test, file SHA-256 `{d['file_sha256']}`.",
             f"**Selected model:** {ev['selected_model']} (rule: {ev['selection_rule']}). **Model version:** `{ev['model_version']}`. **Trained (UTC):** {ev['trained_at_utc']}. **Library versions at training time:** {json.dumps(ev['versions'])}."]
    return "\n".join(rows)

# ---------------- DB
def db_tables():
    cols = psql("select table_name, column_name, data_type, is_nullable, coalesce(column_default,'') from information_schema.columns where table_schema='public' order by table_name, ordinal_position")
    cons = psql("select conrelid::regclass::text, conname, pg_get_constraintdef(oid) from pg_constraint where connamespace='public'::regnamespace and contype in ('p','f','c','u') order by 1,2")
    idx = psql("select tablename, indexname, indexdef from pg_indexes where schemaname='public' order by 1,2")
    by = {}
    for t, c, d, n, df in cols: by.setdefault(t, []).append((c, d, n, df))
    out = []
    for t, cs in by.items():
        out += [f"#### `{t}`", "", "| Column | Type | Null | Default |", "|---|---|---|---|"] + [f"| {c} | {d} | {n} | `{df[:50]}` |" for c, d, n, df in cs]
        out += ["", "Constraints: " + "; ".join(f"`{n}`: {d}" for tb, n, d in cons if tb == t or tb == f"public.{t}"), "", "Indexes: " + "; ".join(f"`{n}`" for tb, n, _ in idx if tb == t), ""]
    return "\n".join(out)
def rls():
    rows = psql("select tablename, policyname, cmd, roles::text, coalesce(qual,''), coalesce(with_check,'') from pg_policies where schemaname='public' order by 1,2")
    st = psql("select policyname, cmd, coalesce(qual,''), coalesce(with_check,'') from pg_policies where schemaname='storage' and tablename='objects' order by 1")
    out = ["| Table | Policy | Command | USING | WITH CHECK |", "|---|---|---|---|---|"]
    out += [f"| {t} | {p} | {c} | `{q}` | `{w}` |" for t, p, c, r_, q, w in rows]
    out += ["", "Storage (`storage.objects`) policies:", "", "| Policy | Command | USING | WITH CHECK |", "|---|---|---|---|"] + [f"| {p} | {c} | `{q[:150]}` | `{w[:150]}` |" for p, c, q, w in st]
    return "\n".join(out)

# ---------------- API (from the real OpenAPI schema)
def api_table():
    from backend.app.main import app
    sch = app.openapi(); out = ["| Method | Endpoint | Summary | Auth | Request body | Success |", "|---|---|---|---|---|---|"]
    auth_free = {"/api/health", "/api/model-info", "/api/chat/suggestions"}
    for path, ops in sorted(sch["paths"].items()):
        for m, o in ops.items():
            body = "multipart/form-data" if "multipart/form-data" in json.dumps(o.get("requestBody", {})) else ("JSON" if "requestBody" in o else "–")
            succ = next((k for k in o["responses"] if k.startswith("2")), "?")
            out.append(f"| {m.upper()} | `{path}` | {o.get('summary', '')} | {'none' if path in auth_free else 'Bearer JWT'}{' (admin)' if '/admin' in path else ' (reviewer/admin)' if path.startswith('/api/knowledge') else ''} | {body} | {succ} |")
    return "\n".join(out)

def diagram(name):
    f = next((ROOT / "docs/diagrams").glob(f"{name}*.mmd"))
    return f"```mermaid\n{f.read_text().strip()}\n```\n\n*(Source: `docs/diagrams/{f.name}`; rendered PNG: `docs/diagrams/png/{f.stem}.png`)*"

def migration(name):
    return "```sql\n" + next((ROOT / "supabase/migrations").glob(f"*{name}*.sql")).read_text() + "\n```"

def jsonfile(n):
    return "```json\n" + (SRC / "examples" / (n + ".json")).read_text().strip() + "\n```"

TOK = {"LIB_TABLE": lib_table, "ML_TABLE": ml_table, "DB_TABLES": db_tables, "RLS_POLICIES": rls, "API_TABLE": api_table}
def render(t):
    t = re.sub(r"\{\{DIAGRAM:([\w]+)\}\}", lambda m: diagram(m[1]), t)
    t = re.sub(r"\{\{JSON:([\w]+)\}\}", lambda m: jsonfile(m[1]), t)
    t = re.sub(r"\{\{MIGRATION:([\w]+)\}\}", lambda m: migration(m[1]), t)
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: "\n\n" + TOK[m[1]]() + "\n\n", t)

for f in sorted(SRC.glob("*.md")):
    (OUT / f.name).write_text(render(f.read_text()))
    print("built", f.name)

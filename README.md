# MediGuide AI — AI for a Healthier Tomorrow
معلومات أوضح .. قرارات أفضل .. صحة أسهل

Educational cardiovascular-health platform (Arabic RTL / English LTR): AI chat with RAG, a scikit-learn heart-risk research model, OCR of lab/ECG/prescription documents, medication-safety review, private patient workspaces (Supabase RLS).
**Educational and research software. Not a diagnostic tool.**

| Folder | Content |
|---|---|
| `app/`, `components/`, `lib/`, `proxy.ts` | Next.js 16 frontend |
| `backend/`, `api/` | FastAPI backend (Vercel entry `api/index.py`) |
| `ml/` | Dataset, training script, saved model, real evaluation reports |
| `supabase/` | Migrations (schema, RLS, storage) |
| `tests/` | pytest (backend) and Playwright (E2E) |
| `docs/` | Academic package, study guide, diagrams, presentation, PDF/DOCX exports |

Quick start, deployment and status: `docs/academic/08_testing_install_deploy.md`. Start reading at `docs/academic/00_README.md`.

```bash
npm install && uv venv --python 3.12 .venv && source .venv/bin/activate && uv pip install -r requirements-dev.txt
npx supabase start && npx supabase db reset      # copy printed keys into .env.local (see .env.example)
uvicorn backend.app.main:app --port 8000 &       # API
npm run dev                                       # http://localhost:3000
python -m pytest tests/backend && npx playwright test
```
Missing for a live deployment: Gemini API key, approved knowledge-base content, hosted Supabase project, Vercel project, OCR worker host.

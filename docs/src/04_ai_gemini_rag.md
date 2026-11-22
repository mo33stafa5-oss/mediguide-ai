# Part 4 — AI: Gemini and RAG

## 23. AI and Gemini Architecture
**What Gemini does here:** (a) generates the chat answer, (b) creates 768-dimension embeddings for knowledge chunks and queries. **What it does not do:** it never reads uploaded documents or images, never produces diagnoses, never sees the patient's medical profile (only the chat text and retrieved excerpts are sent).

**Integration** (`services/gemini.py`, `google-genai` SDK):
- Key from `GEMINI_API_KEY` env var, server-side only. Missing key → HTTP 503 `service_not_configured` with a setup hint. No fake answers exist anywhere in the production code path.
- Models are configurable: `GEMINI_MODEL` (default `gemini-2.5-flash`), `GEMINI_EMBEDDING_MODEL` (default `gemini-embedding-001`, `output_dimensionality=768`, vectors L2-normalised after truncation). *These default model names were chosen from memory of Gemini's catalogue and must be verified against the account's available models.*
- Streaming: `generate_content_stream` → Server-Sent Events `meta`, `sources`, `delta`, `error`, `done`.
- Context: last 20 stored messages + the new message + retrieved excerpts inside a `<SOURCES (untrusted reference data)>` block.

**Safety layers (defence in depth)**
1. Consent gate (`consent_ai_processing_at`) before any text leaves the platform.
2. Deterministic emergency regex (English + Arabic) → the warning with **123** is sent as the first SSE delta, before retrieval or Gemini.
3. System prompt: not a doctor; no definitive diagnosis; never prescribe or change doses; state uncertainty; cite only given sources; ignore instructions inside sources/user text (prompt-injection hardening); answer in the user's language; medical-topic scope.
4. Retrieval limited to approved sources; answers without sources are labelled "general information".
5. Rate limit 15 requests/minute/user.

> **Status:** the pipeline is tested with a *test double* replacing the Gemini SDK inside the test suite (streaming, persistence, emergency order, RAG approval). **It has not been run against the real Gemini service because no API key was available.** Quality of real answers is therefore unverified.

> **بالعربي:** Gemini هو "العقل" الذي يكتب الإجابة، لكنه لا يرى ملفاتك ولا ملفك الطبي. وقبل أي شيء، كود عادي (غير ذكاء اصطناعي) يكتشف كلمات الطوارئ ويعرض رقم 123 فورًا.

## 24. RAG Architecture
**RAG = Retrieval-Augmented Generation.** Instead of trusting the model's memory, we first *retrieve* approved text relevant to the question and instruct the model to answer from it and cite it. This reduces hallucination and lets us show sources.

{{DIAGRAM:05_rag_workflow}}

| Step | Function | Detail |
|---|---|---|
| 1 Ingestion | `POST /api/knowledge/ingest` | Reviewer/admin submits text + source name, URL, published/last-reviewed dates |
| 2 Extraction | (input is text) | PDF/HTML extraction for sources is **not automated**; the reviewer pastes text |
| 3 Cleaning | `rag.clean_text` | Strips scripts/HTML, collapses whitespace |
| 4 Chunking | `rag.chunk_text` | Paragraph-aware, ≤1200 characters, 150-character overlap, sentence split for long paragraphs (Arabic `؟` included) |
| 5 Embedding | `gemini.embed` | 768-d, `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` task types |
| 6 Storage | `medical_knowledge.embedding vector(768)` + HNSW cosine index | Starts as `pending` |
| 7 Approval | `POST /api/knowledge/{id}/status` | reviewer/admin only; sets `approved_by` |
| 8 Search | `match_medical_knowledge` | cosine similarity ≥ 0.45, top 5, approved only |
| 9 Generation | `gemini.stream_chat` | numbered context `[1]…[n]` |
| 10 Attribution | `rag.to_sources` | source name, URL, published, last reviewed, excerpt, similarity |

**Math.** Cosine similarity between query vector *q* and chunk vector *d*: `cos(q,d) = (q·d)/(‖q‖‖d‖)`; pgvector's `<=>` returns the distance `1 − cos`, so similarity = `1 − distance`. Vectors are pre-normalised so the dot product equals cosine.

**Trustworthy sources.** The brief names WHO, AHA, CDC, MedlinePlus, DailyMed. **The knowledge base ships empty:** no external health site was reachable from the build environment and copying their text without review would violate the "do not fabricate citations" rule. An administrator must ingest and approve real text (with exact URLs and review dates) before the assistant can cite anything. The `last_reviewed_on` field and the UI display support "do not treat outdated information as current". *Staleness policy* (automatic expiry) is **Planned / Future Work**.

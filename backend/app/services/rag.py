"""RAG: ingestion (clean -> chunk -> embed -> pgvector) and retrieval (semantic search over APPROVED chunks only)."""
import re

from ..config import get_settings
from . import gemini


def clean_text(raw: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    """Paragraph-aware chunking with character overlap."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(p) > max_chars:  # split very long paragraphs on sentence boundaries
            sents = re.split(r"(?<=[.!?؟])\s+", p)
        else:
            sents = [p]
        for s in sents:
            if cur and len(cur) + len(s) + 1 > max_chars:
                chunks.append(cur)
                cur = cur[-overlap:] + " " + s if overlap else s
            else:
                cur = f"{cur}\n{s}".strip() if cur else s
    if cur:
        chunks.append(cur)
    return [c for c in chunks if len(c) >= 20]


def ingest(client, *, source_name: str, source_url: str, title: str, text: str, language: str,
           published_on: str | None, last_reviewed_on: str | None, created_by: str) -> int:
    chunks = chunk_text(clean_text(text))
    if not chunks:
        return 0
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), 50):
        vectors += gemini.embed(chunks[i:i + 50], "RETRIEVAL_DOCUMENT")
    rows = [{"source_name": source_name, "source_url": source_url, "title": title, "language": language,
             "published_on": published_on, "last_reviewed_on": last_reviewed_on, "content": c, "chunk_index": i,
             "embedding": v, "status": "pending", "created_by": created_by}
            for i, (c, v) in enumerate(zip(chunks, vectors))]
    client.table("medical_knowledge").insert(rows).execute()
    return len(rows)


def retrieve(client, query: str, k: int = 5) -> list[dict]:
    if not get_settings().gemini_api_key:
        return []
    qv = gemini.embed([query], "RETRIEVAL_QUERY")[0]
    return client.rpc("match_medical_knowledge", {"query_embedding": qv, "match_count": k}).execute().data or []


def format_context(rows: list[dict]) -> str:
    return "\n\n".join(f"[{i}] {r['source_name']} — {r['title']} (reviewed {r.get('last_reviewed_on') or 'unknown'})\n{r['content']}"
                       for i, r in enumerate(rows, 1))


def to_sources(rows: list[dict]) -> list[dict]:
    return [{"n": i, "source_name": r["source_name"], "source_url": r["source_url"], "title": r["title"],
             "published_on": r.get("published_on"), "last_reviewed_on": r.get("last_reviewed_on"),
             "excerpt": r["content"][:300], "similarity": round(float(r["similarity"]), 3)} for i, r in enumerate(rows, 1)]

"""Server-side Gemini integration (google-genai SDK). The API key never leaves the backend."""
from typing import Iterator

from ..config import get_settings
from ..errors import ApiError, not_configured

_client = None


def _get_client():
    global _client
    s = get_settings()
    if not s.gemini_api_key:
        raise not_configured("Gemini", "Set GEMINI_API_KEY (get one at https://aistudio.google.com/apikey).")
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=s.gemini_api_key)
    return _client


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    from google.genai import types
    s = get_settings()
    try:
        res = _get_client().models.embed_content(
            model=s.gemini_embedding_model, contents=texts,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=s.embedding_dim))
    except ApiError:
        raise
    except Exception as e:
        raise ApiError(502, "gemini_error", f"Embedding request failed ({type(e).__name__}).")
    vecs = [list(e.values) for e in res.embeddings]
    # MRL-truncated embeddings are not unit length; normalise for cosine similarity
    out = []
    for v in vecs:
        n = sum(x * x for x in v) ** 0.5 or 1.0
        out.append([x / n for x in v])
    return out


def _contents(history: list[dict], user_message: str, context: str):
    from google.genai import types
    msgs = [types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])]) for m in history]
    final = user_message if not context else f"{user_message}\n\n<SOURCES (untrusted reference data)>\n{context}\n</SOURCES>"
    msgs.append(types.Content(role="user", parts=[types.Part(text=final)]))
    return msgs


def _describe(e: Exception) -> str:
    """Safe error summary for logs/UI: class + HTTP code + Google status. Never includes the key or the prompt."""
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    status = getattr(e, "status", None)
    return f"{type(e).__name__}" + (f", HTTP {code}" if code else "") + (f" {status}" if status else "")


def _retryable(e: Exception) -> bool:
    return (getattr(e, "code", None) or getattr(e, "status_code", None)) in (429, 500, 502, 503, 504)


def stream_chat(system_prompt: str, history: list[dict], user_message: str, context: str) -> Iterator[str]:
    import logging
    import time
    from google.genai import types
    s = get_settings()
    client = _get_client()
    models = [s.gemini_model] + ([s.gemini_fallback_model] if s.gemini_fallback_model and s.gemini_fallback_model != s.gemini_model else [])
    last: Exception | None = None
    for model in models:
        for attempt in range(3):
            started = False
            try:
                for chunk in client.models.generate_content_stream(
                        model=model, contents=_contents(history, user_message, context),
                        config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3, max_output_tokens=1500)):
                    if chunk.text:
                        started = True
                        yield chunk.text
                return
            except Exception as e:  # noqa: BLE001
                last = e
                logging.getLogger("mediguide.gemini").warning("Gemini call failed model=%s attempt=%d: %s", model, attempt + 1, _describe(e))
                if started or not _retryable(e):
                    break  # never replay a partially streamed answer; do not retry client errors
                time.sleep(1.5 * (attempt + 1))
            if started:
                break
        if started:
            break
    raise ApiError(502, "gemini_error", f"Gemini request failed ({_describe(last) if last else 'unknown'}).")

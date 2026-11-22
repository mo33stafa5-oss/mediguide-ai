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


def stream_chat(system_prompt: str, history: list[dict], user_message: str, context: str) -> Iterator[str]:
    from google.genai import types
    s = get_settings()
    client = _get_client()
    try:
        for chunk in client.models.generate_content_stream(
                model=s.gemini_model, contents=_contents(history, user_message, context),
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3, max_output_tokens=1500)):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        raise ApiError(502, "gemini_error", f"Gemini request failed ({type(e).__name__}).")

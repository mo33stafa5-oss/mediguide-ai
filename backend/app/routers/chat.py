import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth import User
from ..db import user_client
from ..errors import ApiError, not_configured
from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ChatRequest
from ..services import gemini, rag, safety

log = logging.getLogger("mediguide.chat")
router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/suggestions")
def suggestions(locale: str = "ar"):
    return {"suggestions": safety.SUGGESTED_QUESTIONS.get(locale, safety.SUGGESTED_QUESTIONS["en"])}


@router.post("/chat", dependencies=[Depends(limiter("chat", 15))])
def chat(body: ChatRequest, user: User):
    if not get_settings().gemini_api_key:
        raise not_configured("Gemini", "Set GEMINI_API_KEY on the server.")
    if not user.consent_ai:
        raise ApiError(403, "consent_required", "Please accept AI processing consent in your profile before using the assistant.")
    db = user_client(user.token)
    conv_id = str(body.conversation_id) if body.conversation_id else None
    if conv_id:
        if not db.table("conversations").select("id").eq("id", conv_id).execute().data:  # RLS: only own rows visible
            raise ApiError(404, "conversation_not_found", "Conversation not found.")
    else:
        conv_id = db.table("conversations").insert({"user_id": user.id, "title": body.message[:60]}).execute().data[0]["id"]
    history = db.table("messages").select("role,content").eq("conversation_id", conv_id).order("created_at").limit(20).execute().data
    emergency = safety.is_emergency(body.message)
    db.table("messages").insert({"conversation_id": conv_id, "user_id": user.id, "role": "user", "content": body.message, "is_emergency": emergency}).execute()

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def gen():
        sources: list[dict] = []
        full = ""
        try:
            if emergency:  # deterministic warning first, never delayed by retrieval or the LLM
                notice = safety.EMERGENCY_NOTICE[body.locale] + "\n\n"
                full += notice
                yield sse({"type": "meta", "conversation_id": conv_id, "emergency": True})
                yield sse({"type": "delta", "text": notice})
            else:
                yield sse({"type": "meta", "conversation_id": conv_id, "emergency": False})
            try:
                rows = rag.retrieve(db, body.message)
            except ApiError:
                rows = []  # retrieval failure degrades to no-source answer, flagged below
            sources = rag.to_sources(rows)
            if sources:
                yield sse({"type": "sources", "sources": sources})
            ctx = rag.format_context(rows)
            for piece in gemini.stream_chat(safety.SYSTEM_PROMPT, history, body.message, ctx):
                full += piece
                yield sse({"type": "delta", "text": piece})
            if not sources:
                note = ("\n\n*لم يتم العثور على مصدر معتمد في قاعدة المعرفة لهذا السؤال؛ الإجابة معلومات عامة.*" if body.locale == "ar"
                        else "\n\n*No approved knowledge-base source matched this question; this is general information.*")
                full += note
                yield sse({"type": "delta", "text": note})
        except ApiError as e:
            yield sse({"type": "error", "code": e.detail["code"], "message": e.detail["message"]})
        except Exception as e:
            log.exception("chat stream failed: %s", type(e).__name__)
            yield sse({"type": "error", "code": "internal_error", "message": "Unexpected error."})
        except GeneratorExit:  # client disconnected: still persist what was generated
            _save(db, user.id, conv_id, full, sources, emergency)
            raise
        mid = _save(db, user.id, conv_id, full, sources, emergency)
        if mid:
            yield sse({"type": "done", "message_id": mid})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _save(db, user_id, conv_id, full, sources, emergency):
    if not full.strip():
        return None
    try:
        mid = db.table("messages").insert({"conversation_id": conv_id, "user_id": user_id, "role": "assistant", "content": full,
                                           "sources": sources, "is_emergency": emergency}).execute().data[0]["id"]
        db.table("conversations").update({"updated_at": "now()"}).eq("id", conv_id).execute()
        return mid
    except Exception:
        log.warning("saving assistant message failed")
        return None

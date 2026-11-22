from fastapi import APIRouter

from ..config import get_settings
from ..ocr.engine import ocr_available
from ..services import ml_service

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health():
    s = get_settings()
    try:
        meta = ml_service.model_meta()
        model = {"loaded": True, "version": meta["model_version"]}
    except Exception:
        model = {"loaded": False, "hint": "Run `python -m ml.train`."}
    return {"status": "ok", "services": {
        "supabase": {"configured": s.supabase_configured},
        "gemini": {"configured": bool(s.gemini_api_key), "model": s.gemini_model},
        "ml_model": model,
        "ocr": {"available_in_this_runtime": ocr_available(), "worker_url_configured": bool(s.ocr_worker_url)},
    }}


@router.get("/model-info")
def model_info():
    try:
        meta = ml_service.model_meta()
    except Exception:
        from ..errors import ApiError
        raise ApiError(503, "model_missing", "Model artifact not found. Run `python -m ml.train`.")
    return {**meta, "intended_use": "Education and research only. Not a clinically validated diagnostic tool."}

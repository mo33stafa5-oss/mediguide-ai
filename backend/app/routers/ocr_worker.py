"""Internal OCR endpoint, used when this app runs as the OCR worker (Docker, with Tesseract installed).
Disabled unless OCR_WORKER_TOKEN is set. Stateless: nothing is stored, no medical data is logged."""
import hmac

from fastapi import APIRouter, File, Header, UploadFile

from ..config import get_settings
from ..errors import ApiError
from ..ocr import engine, validate

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/ocr")
async def ocr(file: UploadFile = File(...), x_worker_token: str = Header(default="")):
    token = get_settings().ocr_worker_token
    if not token or not hmac.compare_digest(x_worker_token, token):
        raise ApiError(403, "forbidden", "Invalid worker token.")
    data = await file.read(get_settings().max_upload_bytes + 1)
    mime = validate.sniff_mime(data)
    if mime is None or len(data) > get_settings().max_upload_bytes:
        raise ApiError(422, "invalid_file", "Unsupported or oversized file.")
    try:
        res = engine.extract_text(data, mime)
    except Exception as e:
        raise ApiError(500, "ocr_failed", f"OCR failed ({type(e).__name__}).")
    return {"text": res.text, "mean_confidence": res.mean_confidence, "engine": res.engine, "warnings": res.warnings, "low_conf_words": res.low_conf_words}

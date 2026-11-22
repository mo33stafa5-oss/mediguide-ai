import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..audit import audit
from ..auth import User
from ..config import get_settings
from ..db import user_client
from ..errors import ApiError
from ..ocr import engine, parsers, validate
from ..ratelimit import limiter
from ..schemas import BUCKETS, AnalyzeRequest, DocType

router = APIRouter(prefix="/api/documents", tags=["documents"])

XRAY_NOTICE = ("X-ray analysis is NOT implemented. The image is stored privately and validated, and basic technical metadata is shown. "
               "No diagnosis, finding or AI description is produced. Ask a radiologist.")


@router.post("/upload", status_code=201, dependencies=[Depends(limiter("upload", 10))])
async def upload(user: User, file: UploadFile = File(...), doc_type: DocType = Form(...)):
    s = get_settings()
    data = await file.read(s.max_upload_bytes + 1)
    try:
        info = validate.validate_upload(data, file.filename or "file", s.max_upload_bytes)
    except validate.InvalidFile as e:
        raise ApiError(422, "invalid_file", str(e))
    if doc_type == "xray" and info["mime_type"] == "application/pdf":
        raise ApiError(422, "invalid_file", "X-ray uploads must be JPG or PNG images.")
    doc_id = str(uuid.uuid4())
    bucket = BUCKETS[doc_type]
    path = f"{user.id}/{doc_id}/{validate.safe_filename(file.filename or 'file')}"
    db = user_client(user.token)
    try:
        db.storage.from_(bucket).upload(path, data, {"content-type": info["mime_type"], "upsert": "false"})
    except Exception as e:
        raise ApiError(502, "storage_error", f"Could not store the file ({type(e).__name__}).")
    try:
        row = db.table("medical_documents").insert({
            "id": doc_id, "user_id": user.id, "doc_type": doc_type, "original_name": validate.safe_filename(file.filename or "file"),
            "storage_bucket": bucket, "storage_path": path, "mime_type": info["mime_type"], "size_bytes": info["size_bytes"], "sha256": info["sha256"]}).execute().data[0]
    except Exception:
        db.storage.from_(bucket).remove([path])  # no orphan files
        raise ApiError(500, "db_error", "Could not record the document.")
    audit(user.id, "document.upload", "medical_documents", doc_id, doc_type=doc_type)
    return {"document": row, "file_info": {k: v for k, v in info.items() if k != "sha256"}}


def _load(db, user, document_id: str) -> tuple[dict, bytes]:
    rows = db.table("medical_documents").select("*").eq("id", document_id).execute().data  # RLS-filtered
    if not rows:
        raise ApiError(404, "document_not_found", "Document not found.")
    doc = rows[0]
    try:
        data = db.storage.from_(doc["storage_bucket"]).download(doc["storage_path"])
    except Exception:
        raise ApiError(502, "storage_error", "Could not read the stored file.")
    return doc, data


@router.post("/analyze", dependencies=[Depends(limiter("analyze", 10))])
def analyze(body: AnalyzeRequest, user: User):
    db = user_client(user.token)
    doc, data = _load(db, user, str(body.document_id))
    dt = doc["doc_type"]
    db.table("medical_documents").update({"status": "processing"}).eq("id", doc["id"]).execute()
    extracted: dict = {}
    warnings: list[str] = []
    raw_text, engine_name, detected = None, None, None
    try:
        if dt == "xray":
            from PIL import Image
            import io
            with Image.open(io.BytesIO(data)) as im:
                g = im.convert("L")
                extracted = {"image": {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format},
                             "intensity": {"mean": round(sum(i * c for i, c in enumerate(g.histogram())) / (g.width * g.height), 1)},
                             "diagnosis_performed": False, "note": XRAY_NOTICE}
            warnings.append(XRAY_NOTICE)
            engine_name = "pillow-metadata-only"
        else:
            cfg = get_settings()
            if engine.ocr_available() or doc["mime_type"] == "application/pdf":
                res = engine.extract_text(data, doc["mime_type"])
            elif cfg.ocr_worker_url and cfg.ocr_worker_token:
                try:
                    res = engine.extract_text_remote(data, doc["mime_type"], cfg.ocr_worker_url, cfg.ocr_worker_token)
                except Exception:
                    raise ApiError(502, "ocr_worker_error", "The OCR worker did not respond.")
            else:
                raise ApiError(503, "ocr_unavailable", "OCR engine (Tesseract) is not available in this runtime. Set OCR_WORKER_URL/OCR_WORKER_TOKEN (see docs/DEPLOYMENT).")
            raw_text, engine_name, warnings = res.text, res.engine, list(res.warnings)
            detected, scores = parsers.detect_document_type(res.text)
            if detected and detected != dt:
                warnings.append(f"Content looks like '{detected}' but you uploaded it as '{dt}'. Please check the document type.")
            if dt == "lab":
                extracted = parsers.parse_lab(res.text)
            elif dt == "ecg":
                extracted = parsers.parse_ecg(res.text)
            elif dt == "prescription":
                extracted = parsers.parse_prescription(res.text, res.mean_confidence)
            else:
                extracted = {"note": "General document: text extracted, no structured analysis."}
            extracted["ocr_mean_confidence"] = res.mean_confidence
            extracted["low_confidence_words"] = res.low_conf_words
            warnings += extracted.get("warnings", [])
    except ApiError:
        db.table("medical_documents").update({"status": "failed"}).eq("id", doc["id"]).execute()
        raise
    except Exception as e:
        db.table("medical_documents").update({"status": "failed"}).eq("id", doc["id"]).execute()
        raise ApiError(500, "analysis_failed", f"Analysis failed ({type(e).__name__}).")
    report = db.table("medical_analysis_reports").insert({
        "document_id": doc["id"], "user_id": user.id, "report_type": dt, "ocr_engine": engine_name, "raw_text": raw_text,
        "extracted": extracted, "warnings": warnings}).execute().data[0]
    db.table("medical_documents").update({"status": "needs_review" if (warnings or dt in ("prescription", "lab", "ecg")) else "analyzed",
                                          "detected_type": detected if detected else None}).eq("id", doc["id"]).execute()
    audit(user.id, "document.analyze", "medical_documents", doc["id"], doc_type=dt)
    return {"report": report, "verified": False, "note": "Extracted values are OCR output, not verified medical information."}


@router.get("/{document_id}/url")
def signed_url(document_id: uuid.UUID, user: User):
    db = user_client(user.token)
    rows = db.table("medical_documents").select("storage_bucket,storage_path").eq("id", str(document_id)).execute().data
    if not rows:
        raise ApiError(404, "document_not_found", "Document not found.")
    res = db.storage.from_(rows[0]["storage_bucket"]).create_signed_url(rows[0]["storage_path"], 120)  # 2 minutes
    audit(user.id, "document.view", "medical_documents", str(document_id))
    return {"url": res["signedURL"], "expires_in": 120}


@router.delete("/{document_id}", status_code=204)
def delete(document_id: uuid.UUID, user: User):
    db = user_client(user.token)
    rows = db.table("medical_documents").select("storage_bucket,storage_path").eq("id", str(document_id)).execute().data
    if not rows:
        raise ApiError(404, "document_not_found", "Document not found.")
    db.storage.from_(rows[0]["storage_bucket"]).remove([rows[0]["storage_path"]])
    db.table("medical_documents").delete().eq("id", str(document_id)).execute()  # cascades reports
    audit(user.id, "document.delete", "medical_documents", str(document_id))

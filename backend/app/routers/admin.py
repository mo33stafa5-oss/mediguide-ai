import uuid

from fastapi import APIRouter, Depends

from ..audit import audit
from ..auth import AdminUser, ReviewerUser, User
from ..config import get_settings
from ..db import service_client, user_client
from ..errors import ApiError
from ..ratelimit import limiter
from ..schemas import KnowledgeIngest, KnowledgeStatus, UserAdminUpdate
from ..services import rag

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/knowledge/ingest", status_code=201, dependencies=[Depends(limiter("ingest", 10))])
def ingest(body: KnowledgeIngest, user: ReviewerUser):
    n = rag.ingest(user_client(user.token), source_name=body.source_name, source_url=body.source_url, title=body.title, text=body.text,
                   language=body.language, published_on=body.published_on, last_reviewed_on=body.last_reviewed_on, created_by=user.id)
    audit(user.id, "knowledge.ingest", "medical_knowledge", None, chunks=n, source=body.source_name)
    return {"chunks_created": n, "status": "pending", "note": "Chunks are invisible to patients until approved."}


@router.post("/knowledge/{knowledge_id}/status")
def set_status(knowledge_id: uuid.UUID, body: KnowledgeStatus, user: ReviewerUser):
    patch = {"status": body.status, "approved_by": user.id if body.status == "approved" else None}
    rows = user_client(user.token).table("medical_knowledge").update(patch).eq("id", str(knowledge_id)).execute().data
    if not rows:
        raise ApiError(404, "not_found", "Knowledge chunk not found.")
    audit(user.id, f"knowledge.{body.status}", "medical_knowledge", str(knowledge_id))
    return {"id": str(knowledge_id), "status": body.status}


@router.get("/admin/overview")
def overview(user: AdminUser):
    sc = service_client()
    count = lambda t, **f: (lambda q: q.execute().count)(sc.table(t).select("id", count="exact", head=True) if not f else
                                                         (lambda q: [q := q.eq(k, v) for k, v in f.items()][-1])(sc.table(t).select("id", count="exact", head=True)))
    s = get_settings()
    buckets = []
    try:
        buckets = [b.name for b in sc.storage.list_buckets()]
    except Exception:
        pass
    from ..services import ml_service
    return {"users": count("profiles"), "documents": count("medical_documents"), "conversations": count("conversations"),
            "knowledge_pending": count("medical_knowledge", status="pending"), "knowledge_approved": count("medical_knowledge", status="approved"),
            "storage_buckets": buckets, "gemini_configured": bool(s.gemini_api_key),
            "model": {k: ml_service.model_meta().get(k) for k in ("model_version", "selected_model", "trained_at_utc")},
            "note": "Counts only. Administrators cannot read patients' private medical records."}


@router.get("/admin/users")
def users(user: AdminUser):
    return {"users": service_client().table("profiles").select("id,full_name,role,status,created_at").order("created_at", desc=True).limit(200).execute().data}


@router.patch("/admin/users/{target_id}")
def update_user(target_id: uuid.UUID, body: UserAdminUpdate, user: AdminUser):
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise ApiError(422, "empty_update", "Nothing to update.")
    if str(target_id) == user.id and (patch.get("role") not in (None, "admin") or patch.get("status") == "suspended"):
        raise ApiError(409, "self_lockout", "Administrators cannot demote or suspend themselves.")
    rows = service_client().table("profiles").update(patch).eq("id", str(target_id)).execute().data
    if not rows:
        raise ApiError(404, "not_found", "User not found.")
    audit(user.id, "admin.user_update", "profiles", str(target_id), **patch)
    return rows[0]


@router.get("/admin/audit-logs")
def audit_logs(user: AdminUser):
    return {"logs": user_client(user.token).table("audit_logs").select("*").order("created_at", desc=True).limit(200).execute().data}


@router.get("/admin/evaluation")
def evaluation(user: AdminUser):
    from ..services import ml_service
    return ml_service.model_meta()


@router.delete("/account", status_code=204)
def delete_account(user: User):
    """Right to erasure: delete stored files, then the auth user (rows cascade)."""
    sc = service_client()
    docs = sc.table("medical_documents").select("storage_bucket,storage_path").eq("user_id", user.id).execute().data
    by_bucket: dict[str, list[str]] = {}
    for d in docs:
        by_bucket.setdefault(d["storage_bucket"], []).append(d["storage_path"])
    for b, paths in by_bucket.items():
        sc.storage.from_(b).remove(paths)
    audit(None, "account.delete", "profiles", user.id)  # actor nulled: the account no longer exists
    sc.auth.admin.delete_user(user.id)


@router.get("/account/export")
def export_account(user: User):
    """Data portability: everything the user owns, as JSON (RLS-filtered)."""
    db = user_client(user.token)
    tables = ["profiles", "user_medical_profiles", "conversations", "messages", "medical_documents", "medical_analysis_reports",
              "heart_risk_assessments", "prescriptions", "medication_records"]
    return {t: db.table(t).select("*").execute().data for t in tables}

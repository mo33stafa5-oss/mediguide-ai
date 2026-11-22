from fastapi import APIRouter, Depends

from ..audit import audit
from ..auth import User
from ..db import user_client
from ..errors import ApiError
from ..ratelimit import limiter
from ..schemas import PrescriptionReviewRequest
from ..services import drugs

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


@router.post("/review", dependencies=[Depends(limiter("rx", 20))])
def review(body: PrescriptionReviewRequest, user: User):
    db = user_client(user.token)
    prof = db.table("user_medical_profiles").select("allergies").eq("user_id", user.id).execute().data
    allergies = prof[0]["allergies"] if prof else []
    meds = [m.model_dump() for m in body.medications]
    result = drugs.review(meds, allergies)
    result["allergy_check_performed"] = bool(prof)
    if not prof:
        result["warnings"].append({"type": "no_allergy_info", "severity": "info", "message": "No allergies are recorded in your profile, so no allergy check was possible."})
    result["drug_information"] = [{"name": n, **drugs.dailymed_lookup(n)} for n in sorted({m["name"] for m in meds if m.get("name")})[:8]]
    if body.save:
        if not body.user_confirmed:
            raise ApiError(422, "confirmation_required", "You must confirm the extracted medications before saving them.")
        rx = db.table("prescriptions").insert({"user_id": user.id, "document_id": str(body.document_id) if body.document_id else None,
                                               "confirmed_by_user": True, "review": result}).execute().data[0]
        rows = [{"user_id": user.id, "prescription_id": rx["id"], "name": m["name"], "dosage": m.get("dosage"), "frequency": m.get("frequency"),
                 "duration": m.get("duration"), "ocr_confidence": m.get("ocr_confidence"), "verified": False} for m in meds if m.get("name")]
        if rows:
            db.table("medication_records").insert(rows).execute()
        result["prescription_id"] = rx["id"]
        audit(user.id, "prescription.save", "prescriptions", rx["id"])
    return result

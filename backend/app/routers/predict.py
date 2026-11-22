from fastapi import APIRouter, Depends

from ..auth import User
from ..errors import ApiError
from ..db import user_client
from ..ratelimit import limiter
from ..schemas import HeartInput
from ..services import ml_service

router = APIRouter(prefix="/api", tags=["ml"])

LIMITATIONS = {
    "en": ["Trained on 303 patients from one hospital (Cleveland, 1980s); may not generalise to you.",
           "Output is a model score, NOT a clinically validated probability or a diagnosis.",
           "Cannot account for many real risk factors (smoking, family history, medications, etc.)."],
    "ar": ["تم تدريب النموذج على 303 مريضًا من مستشفى واحد (كليفلاند، الثمانينيات) وقد لا ينطبق عليك.",
           "النتيجة درجة من نموذج تعليمي وليست احتمالًا مُعتمدًا إكلينيكيًا ولا تشخيصًا.",
           "لا يأخذ النموذج في الاعتبار عوامل كثيرة (التدخين، التاريخ العائلي، الأدوية...)."],
}
RECOMMENDATIONS = {
    "en": ["Discuss your results with a doctor, whatever the score.", "Know the heart-attack warning signs; call 123 in an emergency.",
           "General prevention: regular activity, balanced diet, no smoking, regular blood-pressure and cholesterol checks."],
    "ar": ["ناقش نتائجك مع الطبيب أيًا كانت الدرجة.", "تعرّف على علامات النوبة القلبية واتصل بـ 123 في الطوارئ.",
           "وقاية عامة: نشاط بدني منتظم، غذاء متوازن، الإقلاع عن التدخين، فحص الضغط والكوليسترول بانتظام."],
}


@router.post("/predict", dependencies=[Depends(limiter("predict", 20))])
def predict(body: HeartInput, user: User):
    try:
        result = ml_service.predict(body.model_dump())
    except FileNotFoundError:
        raise ApiError(503, "model_missing", "Model artifact not found. Run `python -m ml.train`.")
    meta = ml_service.model_meta()
    row = user_client(user.token).table("heart_risk_assessments").insert(
        {"user_id": user.id, "inputs": body.model_dump(), "prediction": result["prediction"], "score": result["score"], "model_version": result["model_version"]}).execute().data[0]
    return {**result, "assessment_id": row["id"], "label": "higher_risk_pattern" if result["prediction"] else "lower_risk_pattern",
            "explanation": {"en": "The model compares your inputs with patterns in the training data. A higher score means your inputs resemble patients in the dataset who had heart disease.",
                            "ar": "يقارن النموذج مدخلاتك بأنماط في بيانات التدريب. الدرجة الأعلى تعني أن مدخلاتك تشبه مرضى في البيانات كانت لديهم أمراض قلب."},
            "test_metrics_of_selected_model": meta["results"][meta["selected_model"]]["test"],
            "limitations": LIMITATIONS, "recommendations": RECOMMENDATIONS,
            "disclaimer": {"en": "Educational/research tool. Not a diagnosis. Consult a qualified doctor.", "ar": "أداة تعليمية/بحثية وليست تشخيصًا. استشر طبيبًا مختصًا."}}

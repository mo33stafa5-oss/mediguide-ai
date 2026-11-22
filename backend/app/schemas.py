from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

DocType = Literal["xray", "ecg", "lab", "prescription", "general"]
BUCKETS = {"xray": "xray-images", "ecg": "ecg-reports", "lab": "lab-reports", "prescription": "prescriptions", "general": "general-documents"}


class HeartInput(BaseModel):
    """UCI Cleveland-compatible inputs, each range-validated."""
    age: int = Field(ge=18, le=100)
    sex: Literal[0, 1]
    cp: Literal[1, 2, 3, 4]
    trestbps: int = Field(ge=70, le=250)
    chol: int = Field(ge=80, le=700)
    fbs: Literal[0, 1]
    restecg: Literal[0, 1, 2]
    thalach: int = Field(ge=60, le=230)
    exang: Literal[0, 1]
    oldpeak: float = Field(ge=0, le=7)
    slope: Literal[1, 2, 3]
    ca: int = Field(ge=0, le=3)
    thal: Literal[3, 6, 7]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    locale: Literal["ar", "en"] = "ar"

    @field_validator("message")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


class AnalyzeRequest(BaseModel):
    document_id: UUID


class MedicationIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    duration: str | None = Field(default=None, max_length=100)
    source_line: str | None = Field(default=None, max_length=500)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = []


class PrescriptionReviewRequest(BaseModel):
    document_id: UUID | None = None
    medications: list[MedicationIn] = Field(min_length=1, max_length=40)
    user_confirmed: bool = False   # human confirmation of OCR output; required to save
    save: bool = False


class KnowledgeIngest(BaseModel):
    source_name: str = Field(min_length=2, max_length=200)
    source_url: str = Field(pattern=r"^https?://\S+$", max_length=500)
    title: str = Field(min_length=2, max_length=300)
    text: str = Field(min_length=50, max_length=200_000)
    language: Literal["ar", "en"] = "en"
    published_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    last_reviewed_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class KnowledgeStatus(BaseModel):
    status: Literal["approved", "rejected", "archived", "pending"]


class UserAdminUpdate(BaseModel):
    role: Literal["patient", "admin", "medical_reviewer"] | None = None
    status: Literal["active", "suspended"] | None = None

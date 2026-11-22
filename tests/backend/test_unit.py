import io

import pytest
from PIL import Image

from backend.app.ocr import parsers, validate
from backend.app.services import drugs, rag, safety


# ---------- medical safety ----------
@pytest.mark.parametrize("text", ["I have crushing chest pain and my left arm hurts", "عندي ألم في الصدر وضيق في التنفس", "I think I'm having a heart attack"])
def test_emergency_detected(text):
    assert safety.is_emergency(text)


@pytest.mark.parametrize("text", ["What is LDL cholesterol?", "ما هو ضغط الدم الطبيعي؟"])
def test_non_emergency(text):
    assert not safety.is_emergency(text)


def test_emergency_notice_has_egypt_number():
    assert "123" in safety.EMERGENCY_NOTICE["ar"] and "123" in safety.EMERGENCY_NOTICE["en"]


def test_system_prompt_forbids_prescribing_and_dosing():
    p = safety.SYSTEM_PROMPT.lower()
    assert "never prescribe" in p and "changing the dose" in p and "not a doctor" in p


# ---------- RAG pure functions ----------
def test_chunking_respects_size_and_overlap():
    text = "\n\n".join(f"Paragraph {i}. " + "Blood pressure is the force of blood. " * 12 for i in range(10))
    chunks = rag.chunk_text(text, max_chars=600, overlap=80)
    assert len(chunks) > 3 and all(len(c) <= 600 + 80 + 100 for c in chunks)


def test_clean_text_strips_html():
    assert rag.clean_text("<script>x()</script><p>Hello   <b>world</b></p>") == "Hello world"


# ---------- file validation ----------
def _png(w=200, h=200):
    b = io.BytesIO(); Image.new("RGB", (w, h), "white").save(b, "PNG"); return b.getvalue()


def test_valid_png_accepted():
    assert validate.validate_upload(_png(), "a.png", 1_000_000)["mime_type"] == "image/png"


def test_extension_mismatch_rejected():
    with pytest.raises(validate.InvalidFile):
        validate.validate_upload(_png(), "a.pdf", 1_000_000)


def test_executable_masquerading_as_image_rejected():
    with pytest.raises(validate.InvalidFile):
        validate.validate_upload(b"MZ\x90\x00" + b"\x00" * 500, "a.png", 1_000_000)


def test_oversize_rejected():
    with pytest.raises(validate.InvalidFile):
        validate.validate_upload(_png(), "a.png", 100)


def test_truncated_png_rejected():
    with pytest.raises(validate.InvalidFile):
        validate.validate_upload(_png()[:80], "a.png", 1_000_000)


def test_dicom_not_supported():
    assert validate.sniff_mime(b"\x00" * 128 + b"DICM") is None


def test_safe_filename_blocks_traversal():
    assert "/" not in validate.safe_filename("../../etc/passwd") and not validate.safe_filename("../../x").startswith(".")


# ---------- parsers (pure text input) ----------
LAB = """Patient Lab Report Date: 2026-03-02
Total Cholesterol 245 mg/dL (125 - 200)
HDL 38 mg/dL (40 - 60)
Glucose 92 mg/dL (70 - 99)
Hemoglobin 13.5 g/dL
"""


def test_lab_flags_only_with_printed_range():
    r = parsers.parse_lab(LAB)
    by = {x["test"]: x for x in r["results"]}
    assert by["Total Cholesterol"]["status"] == "high"
    assert by["HDL"]["status"] == "low"
    assert by["Glucose"]["status"] == "within_range"
    assert by["Hemoglobin"]["status"] == "unknown" and by["Hemoglobin"]["reference_low"] is None  # never invent a range
    assert r["report_date"] == "2026-03-02"


def test_ecg_extracts_printed_values_and_ignores_implausible():
    r = parsers.parse_ecg("ECG Report\nHeart Rate: 72 bpm\nPR 160 ms\nQRS 92 ms\nQTc 430 ms\nQT 9999")
    m = r["measurements"]
    assert m["heart_rate_bpm"]["value"] == 72 and m["qtc_ms"]["value"] == 430 and "qt_ms" not in m


def test_ecg_empty_has_warning_no_invented_values():
    r = parsers.parse_ecg("blurry")
    assert r["measurements"] == {} and r["warnings"]


def test_prescription_extraction_and_uncertainty():
    r = parsers.parse_prescription("Tab Atorvastatin 20 mg once daily for 30 days\nTab Metoprolol\nBisoprlol 5 mg")
    names = {m["name"]: m for m in r["medications"]}
    assert names["atorvastatin"]["dosage"] == "20 mg" and names["atorvastatin"]["duration"] == "30 days"
    assert any("Dosage missing" in w for w in names["metoprolol"]["warnings"])
    assert "bisoprolol" in names and any("approximately" in w for w in names["bisoprolol"]["warnings"])
    assert r["requires_user_confirmation"] is True


def test_prescription_unrecognised_not_guessed():
    r = parsers.parse_prescription("Xqzvbn 10 mg daily")
    assert r["medications"][0]["name"] is None and r["medications"][0]["warnings"]


def test_document_type_detection():
    assert parsers.detect_document_type(LAB)[0] == "lab"
    assert parsers.detect_document_type("ECG QRS QTc sinus rhythm")[0] == "ecg"
    assert parsers.detect_document_type("hello world")[0] is None


# ---------- medication safety ----------
def test_duplicate_allergy_missing_dose_and_interaction():
    meds = [{"name": "warfarin", "dosage": "5 mg", "frequency": "daily"}, {"name": "aspirin", "dosage": None, "frequency": None},
            {"name": "aspirin", "dosage": "75 mg", "frequency": "daily"}]
    r = drugs.review(meds, ["Aspirin"])
    types = {w["type"] for w in r["warnings"]}
    assert {"duplicate", "allergy", "missing_dosage"} <= types
    assert any(set(i["drugs"]) >= {"warfarin", "aspirin"} for i in r["interactions"])
    assert "pharmacist" in r["pharmacist_notice"]["en"].lower()
    assert "NOT exhaustive" in r["coverage_note"]


def test_no_interaction_is_not_called_safe():
    r = drugs.review([{"name": "amlodipine", "dosage": "5 mg", "frequency": "daily"}], [])
    assert r["interactions"] == [] and "not mean" in r["coverage_note"]


def test_vercel_requirements_in_sync():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    strip = lambda p: [l for l in (root / p).read_text().splitlines() if l and not l.startswith("#")]
    assert strip("requirements.txt") == strip("backend/requirements.txt")

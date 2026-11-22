"""Integration tests against the REAL local Supabase stack (Auth, Postgres+RLS, Storage). Gemini is replaced by a
test double ONLY inside these tests to exercise the pipeline; production code never fakes responses."""
import io
import json

import httpx
import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.app.ocr.engine import ocr_available
from backend.app.services import gemini
from .conftest import ANON, SERVICE, URL, make_user, needs_db

pytestmark = [needs_db, pytest.mark.integration]
needs_ocr = pytest.mark.skipif(not ocr_available(), reason="Tesseract not installed in this runtime (e.g. Vercel-like env)")
SAMPLE = dict(age=63, sex=1, cp=1, trestbps=145, chol=233, fbs=1, restecg=2, thalach=150, exang=0, oldpeak=2.3, slope=3, ca=0, thal=6)


def rest(person, path, method="GET", **kw):
    h = {"apikey": ANON, "Authorization": f"Bearer {person.token}", "Content-Type": "application/json", "Prefer": "return=representation"}
    return httpx.request(method, f"{URL}/rest/v1/{path}", headers=h, **kw)


def text_png(lines, size=(1400, 900)) -> bytes:
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    for i, l in enumerate(lines):
        d.text((40, 40 + i * 70), l, fill="black", font=f)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


# ---------------- authentication ----------------
def test_missing_and_bad_token(client):
    assert client.post("/api/predict", json=SAMPLE).status_code == 401
    r = client.post("/api/predict", json=SAMPLE, headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_profile_auto_created_as_patient(alice):
    p = rest(alice, f"profiles?id=eq.{alice.id}").json()
    assert p[0]["role"] == "patient" and p[0]["consent_terms_at"]


def test_user_cannot_escalate_role(alice):
    r = rest(alice, f"profiles?id=eq.{alice.id}", "PATCH", json={"role": "admin"})
    assert r.status_code >= 400 or r.json() == [] or r.json()[0]["role"] == "patient"
    assert rest(alice, f"profiles?id=eq.{alice.id}").json()[0]["role"] == "patient"


# ---------------- predict ----------------
def test_predict_ok_saved_and_validated(client, alice):
    r = client.post("/api/predict", json=SAMPLE, headers=alice.h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert 0 <= j["score"] <= 1 and j["model_version"] and j["limitations"]["en"] and "Not a diagnosis" in j["disclaimer"]["en"]
    assert len(rest(alice, "heart_risk_assessments").json()) >= 1


def test_predict_validation_errors(client, alice):
    r = client.post("/api/predict", json={**SAMPLE, "age": 5, "cp": 9}, headers=alice.h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert {f["field"] for f in r.json()["error"]["fields"]} >= {"age", "cp"}


# ---------------- RLS isolation ----------------
def test_rls_patients_cannot_see_each_others_rows(client, alice, bob):
    client.post("/api/predict", json=SAMPLE, headers=alice.h)
    assert rest(bob, "heart_risk_assessments").json() == []
    assert rest(bob, f"heart_risk_assessments?user_id=eq.{alice.id}").json() == []
    assert len(rest(bob, "profiles").json()) == 1  # only own profile


def test_rls_cannot_insert_for_other_user(alice, bob):
    r = rest(bob, "conversations", "POST", json={"user_id": alice.id, "title": "x"})
    assert r.status_code in (401, 403)


def test_rls_cannot_update_or_delete_others_rows(client, alice, bob):
    conv = rest(alice, "conversations", "POST", json={"user_id": alice.id, "title": "mine"}).json()[0]
    assert rest(bob, f"conversations?id=eq.{conv['id']}", "PATCH", json={"title": "pwn"}).json() == []
    assert rest(bob, f"conversations?id=eq.{conv['id']}", "DELETE").json() == []
    assert rest(alice, f"conversations?id=eq.{conv['id']}").json()[0]["title"] == "mine"


def test_cannot_attach_message_to_foreign_conversation(alice, bob):
    conv = rest(alice, "conversations", "POST", json={"user_id": alice.id, "title": "mine"}).json()[0]
    r = rest(bob, "messages", "POST", json={"conversation_id": conv["id"], "user_id": bob.id, "role": "user", "content": "hi"})
    assert r.status_code >= 400


def test_admin_cannot_read_patient_private_data(client, alice, admin):
    rest(alice, "conversations", "POST", json={"user_id": alice.id, "title": "private"})
    assert rest(admin, f"conversations?user_id=eq.{alice.id}").json() == []
    assert rest(admin, f"heart_risk_assessments?user_id=eq.{alice.id}").json() == []
    assert len(rest(admin, "profiles").json()) > 1  # admin can manage accounts


def test_anon_has_no_access():
    r = httpx.get(f"{URL}/rest/v1/profiles", headers={"apikey": ANON})
    assert r.status_code in (401, 403) or r.json() == []


# ---------------- storage + documents ----------------
def test_upload_validation_rejects_bad_files(client, alice):
    r = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "lab"}, files={"file": ("x.png", b"MZ" + b"0" * 500, "image/png")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_file"
    r = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "xray"}, files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 422


@needs_ocr
def test_lab_upload_ocr_end_to_end_and_signed_url_and_delete(client, alice, bob):
    png = text_png(["Lipid Panel  Date: 2026-03-02", "Total Cholesterol 245 mg/dL (125 - 200)", "HDL 38 mg/dL (40 - 60)", "Glucose 92 mg/dL (70 - 99)"])
    up = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "lab"}, files={"file": ("lab.png", png, "image/png")})
    assert up.status_code == 201, up.text
    doc = up.json()["document"]
    assert doc["storage_bucket"] == "lab-reports" and doc["storage_path"].startswith(alice.id + "/")
    # Bob cannot analyze, sign, or delete Alice's document
    assert client.post("/api/documents/analyze", headers=bob.h, json={"document_id": doc["id"]}).status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/url", headers=bob.h).status_code == 404
    assert client.delete(f"/api/documents/{doc['id']}", headers=bob.h).status_code == 404
    # direct storage access is blocked for Bob, and the bucket is private
    assert httpx.get(f"{URL}/storage/v1/object/lab-reports/{doc['storage_path']}", headers={"apikey": ANON, "Authorization": f"Bearer {bob.token}"}).status_code in (400, 401, 403, 404)
    assert httpx.get(f"{URL}/storage/v1/object/public/lab-reports/{doc['storage_path']}").status_code in (400, 404)
    # OCR by Alice
    an = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": doc["id"]})
    assert an.status_code == 200, an.text
    rep = an.json()["report"]
    tests = {r["test"].lower(): r for r in rep["extracted"].get("results", [])}
    assert an.json()["verified"] is False
    chol = next((v for k, v in tests.items() if "cholesterol" in k), None)
    assert chol and chol["value"] == 245 and chol["status"] == "high", rep["extracted"]
    # signed URL works for owner and is short-lived
    u = client.get(f"/api/documents/{doc['id']}/url", headers=alice.h).json()
    assert u["expires_in"] <= 300 and httpx.get(f"{URL}/storage/v1{u['url']}" if u["url"].startswith("/") else u["url"]).status_code == 200
    # delete removes file + rows
    assert client.delete(f"/api/documents/{doc['id']}", headers=alice.h).status_code == 204
    assert rest(alice, f"medical_documents?id=eq.{doc['id']}").json() == []
    assert httpx.get(f"{URL}/storage/v1/object/authenticated/lab-reports/{doc['storage_path']}", headers={"apikey": ANON, "Authorization": f"Bearer {alice.token}"}).status_code in (400, 404)


def test_xray_workflow_never_diagnoses(client, alice):
    png = text_png(["X"], size=(400, 400))
    d = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "xray"}, files={"file": ("xr.png", png, "image/png")}).json()["document"]
    an = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": d["id"]}).json()["report"]
    assert an["extracted"]["diagnosis_performed"] is False and "NOT implemented" in an["warnings"][0]


@needs_ocr
def test_ecg_image_ocr_extracts_printed_numbers(client, alice):
    png = text_png(["ECG REPORT", "Heart Rate: 72 bpm", "PR interval: 160 ms", "QRS duration: 92 ms", "QTc: 430 ms"])
    d = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "ecg"}, files={"file": ("ecg.png", png, "image/png")}).json()["document"]
    rep = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": d["id"]}).json()["report"]
    m = rep["extracted"]["measurements"]
    assert m.get("heart_rate_bpm", {}).get("value") == 72 and "No waveform" in rep["extracted"]["disclaimer"], rep["extracted"]


def test_prescription_review_flow_requires_confirmation(client, alice):
    meds = [{"name": "warfarin", "dosage": "5 mg", "frequency": "daily"}, {"name": "ibuprofen", "dosage": None, "frequency": None}]
    r = client.post("/api/prescriptions/review", headers=alice.h, json={"medications": meds}).json()
    assert r["interactions"] and "pharmacist" in r["pharmacist_notice"]["en"].lower()
    assert any(w["type"] == "no_allergy_info" for w in r["warnings"])
    assert all(d["status"] in ("ok", "unavailable") for d in r["drug_information"])  # honest when DailyMed is unreachable
    assert client.post("/api/prescriptions/review", headers=alice.h, json={"medications": meds, "save": True}).status_code == 422
    ok = client.post("/api/prescriptions/review", headers=alice.h, json={"medications": meds, "save": True, "user_confirmed": True}).json()
    assert rest(alice, f"medication_records?prescription_id=eq.{ok['prescription_id']}").json()


def test_allergy_check_uses_profile(client, alice):
    rest(alice, "user_medical_profiles", "POST", json={"user_id": alice.id, "allergies": ["aspirin"]})
    r = client.post("/api/prescriptions/review", headers=alice.h, json={"medications": [{"name": "aspirin", "dosage": "75 mg", "frequency": "daily"}]}).json()
    assert any(w["type"] == "allergy" and w["severity"] == "critical" for w in r["warnings"])


# ---------------- chat ----------------
def test_chat_without_gemini_key_is_clear_503(client, alice):
    r = client.post("/api/chat", headers=alice.h, json={"message": "hello"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "service_not_configured" and "GEMINI_API_KEY" in r.json()["error"]["message"]


@pytest.fixture
def fake_gemini(monkeypatch):
    from backend.app import config
    monkeypatch.setenv("GEMINI_API_KEY", "test-double")
    config.get_settings.cache_clear()
    monkeypatch.setattr(gemini, "embed", lambda texts, task="RETRIEVAL_DOCUMENT": [[1.0] + [0.0] * 767 for _ in texts])
    monkeypatch.setattr(gemini, "stream_chat", lambda sp, h, m, c: iter(["Test ", "reply."]))
    yield
    config.get_settings.cache_clear()


def _events(resp):
    return [json.loads(l[6:]) for l in resp.text.splitlines() if l.startswith("data: ")]


def test_chat_requires_consent(client, fake_gemini):
    nc = make_user(consent_ai=False)
    r = client.post("/api/chat", headers=nc.h, json={"message": "hello"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "consent_required"


def test_chat_stream_persist_and_isolation(client, alice, bob, fake_gemini):
    r = client.post("/api/chat", headers=alice.h, json={"message": "What is LDL?", "locale": "en"})
    ev = _events(r)
    assert ev[0]["type"] == "meta" and ev[-1]["type"] == "done"
    assert "".join(e["text"] for e in ev if e["type"] == "delta").startswith("Test reply.")
    cid = ev[0]["conversation_id"]
    assert len(rest(alice, f"messages?conversation_id=eq.{cid}").json()) == 2
    assert rest(bob, f"messages?conversation_id=eq.{cid}").json() == []
    r2 = client.post("/api/chat", headers=bob.h, json={"message": "hi", "conversation_id": cid})
    assert r2.status_code == 404


def test_chat_emergency_warning_first_with_123(client, alice, fake_gemini):
    ev = _events(client.post("/api/chat", headers=alice.h, json={"message": "I have severe chest pain", "locale": "en"}))
    assert ev[0]["emergency"] is True and "123" in ev[1]["text"] and "Emergency" in ev[1]["text"]


def test_rag_only_approved_chunks_retrieved(client, alice, admin, fake_gemini):
    httpx.delete(f"{URL}/rest/v1/medical_knowledge?id=not.is.null", headers={"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}"}).raise_for_status()  # clean slate
    ing = client.post("/api/knowledge/ingest", headers=admin.h, json={
        "source_name": "Test Source", "source_url": "https://example.org/x", "title": "LDL", "language": "en",
        "text": "LDL cholesterol is often called bad cholesterol because high levels raise cardiovascular risk. " * 3, "last_reviewed_on": "2026-01-01"})
    assert ing.status_code == 201
    pend = rest(admin, "medical_knowledge?status=eq.pending&select=id").json()
    assert pend and rest(alice, "medical_knowledge?select=id").json() == []  # patients cannot see pending chunks
    ev = _events(client.post("/api/chat", headers=alice.h, json={"message": "LDL?", "locale": "en"}))
    assert not any(e["type"] == "sources" for e in ev)
    assert client.post(f"/api/knowledge/{pend[0]['id']}/status", headers=alice.h, json={"status": "approved"}).status_code == 403
    assert client.post(f"/api/knowledge/{pend[0]['id']}/status", headers=admin.h, json={"status": "approved"}).status_code == 200
    ev = _events(client.post("/api/chat", headers=alice.h, json={"message": "LDL?", "locale": "en"}))
    src = next(e for e in ev if e["type"] == "sources")["sources"]
    assert src[0]["source_url"] == "https://example.org/x" and src[0]["source_name"] == "Test Source"


# ---------------- admin + account ----------------
def test_admin_endpoints_forbidden_for_patients(client, alice):
    for path in ("/api/admin/overview", "/api/admin/users", "/api/admin/audit-logs"):
        assert client.get(path, headers=alice.h).status_code == 403


def test_admin_overview_and_user_management(client, admin):
    assert client.get("/api/admin/overview", headers=admin.h).json()["users"] >= 3
    tgt = make_user()
    r = client.patch(f"/api/admin/users/{tgt.id}", headers=admin.h, json={"status": "suspended"})
    assert r.status_code == 200
    assert client.post("/api/predict", json=SAMPLE, headers=tgt.h).status_code == 403  # suspended accounts blocked server-side
    assert client.patch(f"/api/admin/users/{admin.id}", headers=admin.h, json={"role": "patient"}).status_code == 409
    assert any(l["action"] == "admin.user_update" for l in client.get("/api/admin/audit-logs", headers=admin.h).json()["logs"])


def test_account_export_and_deletion(client):
    u = make_user()
    client.post("/api/predict", json=SAMPLE, headers=u.h)
    assert client.get("/api/account/export", headers=u.h).json()["heart_risk_assessments"]
    assert client.delete("/api/account", headers=u.h).status_code == 204
    assert client.post("/api/predict", json=SAMPLE, headers=u.h).status_code == 401
    sh = {"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}"}
    assert httpx.get(f"{URL}/rest/v1/heart_risk_assessments?user_id=eq.{u.id}", headers=sh).json() == []


def test_rate_limit(client):
    from backend.app import ratelimit
    for _ in range(3):
        ratelimit.check("t:unit", 3)
    with pytest.raises(Exception) as e:
        ratelimit.check("t:unit", 3)
    assert e.value.status_code == 429


def test_error_does_not_leak_internal_details(client, alice):
    r = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": "not-a-uuid"})
    assert r.status_code == 422 and "Traceback" not in r.text


@needs_ocr
def test_ocr_worker_token_protection_and_delegation(client, alice, monkeypatch):
    from backend.app import config
    from backend.app.ocr import engine
    png = text_png(["ECG REPORT", "Heart Rate: 72 bpm"])
    monkeypatch.setenv("OCR_WORKER_TOKEN", "s3cret")
    config.get_settings.cache_clear()
    assert client.post("/internal/ocr", files={"file": ("a.png", png, "image/png")}).status_code == 403
    assert client.post("/internal/ocr", headers={"X-Worker-Token": "wrong"}, files={"file": ("a.png", png, "image/png")}).status_code == 403
    ok = client.post("/internal/ocr", headers={"X-Worker-Token": "s3cret"}, files={"file": ("a.png", png, "image/png")})
    assert ok.status_code == 200 and "Heart" in ok.json()["text"]
    # API -> worker delegation when local OCR is unavailable (worker call routed to the in-process app)
    monkeypatch.setenv("OCR_WORKER_URL", "http://worker.test")
    config.get_settings.cache_clear()
    real = engine.ocr_available
    monkeypatch.setattr(engine, "ocr_available", lambda: False)  # the API runtime has no Tesseract (like Vercel)
    def fake_post(url, headers, files, timeout):
        assert url == "http://worker.test/internal/ocr"
        monkeypatch.setattr(engine, "ocr_available", real)       # the worker runtime has Tesseract
        try:
            r = client.post("/internal/ocr", headers=headers, files=files)
        finally:
            monkeypatch.setattr(engine, "ocr_available", lambda: False)
        r.raise_for_status = lambda: None
        return r
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    d = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "ecg"}, files={"file": ("e.png", png, "image/png")}).json()["document"]
    rep = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": d["id"]})
    assert rep.status_code == 200 and rep.json()["report"]["ocr_engine"].endswith("@worker")
    config.get_settings.cache_clear()


def test_ocr_unavailable_runtime_gives_clear_503(client, alice, monkeypatch):
    from backend.app import config
    from backend.app.ocr import engine
    monkeypatch.setenv("OCR_WORKER_URL", "")
    config.get_settings.cache_clear()
    monkeypatch.setattr(engine, "ocr_available", lambda: False)
    png = text_png(["ECG REPORT", "Heart Rate: 72 bpm"], size=(600, 300))
    d = client.post("/api/documents/upload", headers=alice.h, data={"doc_type": "ecg"}, files={"file": ("e.png", png, "image/png")}).json()["document"]
    r = client.post("/api/documents/analyze", headers=alice.h, json={"document_id": d["id"]})
    assert r.status_code == 503 and r.json()["error"]["code"] == "ocr_unavailable"
    assert rest(alice, f"medical_documents?id=eq.{d['id']}").json()[0]["status"] == "failed"
    config.get_settings.cache_clear()

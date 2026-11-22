import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings

URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
ANON = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH")
SERVICE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
os.environ.update(SUPABASE_URL=URL, SUPABASE_ANON_KEY=ANON, SUPABASE_SERVICE_ROLE_KEY=SERVICE, GEMINI_API_KEY="")
get_settings.cache_clear()


def supabase_up() -> bool:
    try:
        return httpx.get(f"{URL}/auth/v1/health", headers={"apikey": ANON}, timeout=2).status_code == 200
    except Exception:
        return False


needs_db = pytest.mark.skipif(not supabase_up(), reason="local Supabase not running")


class Person:
    def __init__(self, email, password, uid, token):
        self.email, self.password, self.id, self.token = email, password, uid, token

    @property
    def h(self):
        return {"Authorization": f"Bearer {self.token}"}


def make_user(role="patient", consent_ai=True) -> Person:
    email, pw = f"t{uuid.uuid4().hex[:10]}@example.test", "Passw0rd-test1"
    r = httpx.post(f"{URL}/auth/v1/admin/users", headers={"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}"},
                   json={"email": email, "password": pw, "email_confirm": True, "user_metadata": {"full_name": "Test", "consent_terms": "true"}})
    r.raise_for_status()
    uid = r.json()["id"]
    sh = {"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}", "Prefer": "return=minimal", "Content-Type": "application/json"}
    patch = {}
    if role != "patient":
        patch["role"] = role
    if consent_ai:
        patch["consent_ai_processing_at"] = "2026-01-01T00:00:00Z"
    if patch:
        httpx.patch(f"{URL}/rest/v1/profiles?id=eq.{uid}", headers=sh, json=patch).raise_for_status()
    t = httpx.post(f"{URL}/auth/v1/token?grant_type=password", headers={"apikey": ANON}, json={"email": email, "password": pw})
    t.raise_for_status()
    return Person(email, pw, uid, t.json()["access_token"])


@pytest.fixture(scope="session")
def client():
    from backend.app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def alice():
    return make_user()


@pytest.fixture(scope="session")
def bob():
    return make_user()


@pytest.fixture(scope="session")
def admin():
    return make_user("admin")

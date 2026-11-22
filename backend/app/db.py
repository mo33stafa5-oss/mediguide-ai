"""Supabase clients. User-scoped clients carry the caller's JWT so Postgres RLS applies."""
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from .config import get_settings
from .errors import not_configured


def user_client(token: str) -> Client:
    s = get_settings()
    if not s.supabase_configured:
        raise not_configured("Supabase", "Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    return create_client(s.supabase_url, s.supabase_anon_key,
                         options=SyncClientOptions(headers={"Authorization": f"Bearer {token}"}, auto_refresh_token=False, persist_session=False))


def service_client() -> Client:
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_role_key):
        raise not_configured("Supabase service role", "Set SUPABASE_SERVICE_ROLE_KEY (server only).")
    return create_client(s.supabase_url, s.supabase_service_role_key,
                         options=SyncClientOptions(auto_refresh_token=False, persist_session=False))

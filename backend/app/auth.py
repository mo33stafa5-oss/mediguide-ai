"""Authentication: validate the Supabase access token server-side, then load the role from `profiles`."""
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

from .config import get_settings
from .db import user_client
from .errors import ApiError, not_configured


@dataclass
class CurrentUser:
    id: str
    email: str | None
    token: str
    role: str
    locale: str
    consent_ai: bool


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    if not get_settings().supabase_configured:
        raise not_configured("Authentication", "Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthenticated", "Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    client = user_client(token)
    try:
        res = client.auth.get_user(token)  # verified by Supabase Auth, not just decoded
    except Exception:
        raise ApiError(401, "invalid_token", "Invalid or expired session.")
    if not res or not res.user:
        raise ApiError(401, "invalid_token", "Invalid or expired session.")
    prof = client.table("profiles").select("role,status,locale,consent_ai_processing_at").eq("id", res.user.id).limit(1).execute().data
    if not prof:
        raise ApiError(403, "no_profile", "Profile not found.")
    if prof[0]["status"] != "active":
        raise ApiError(403, "account_suspended", "This account is suspended.")
    return CurrentUser(res.user.id, res.user.email, token, prof[0]["role"], prof[0]["locale"], bool(prof[0]["consent_ai_processing_at"]))


def require_roles(*roles: str):
    def dep(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise ApiError(403, "forbidden", "You do not have permission for this action.")
        return user
    return dep


User = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_roles("admin"))]
ReviewerUser = Annotated[CurrentUser, Depends(require_roles("admin", "medical_reviewer"))]

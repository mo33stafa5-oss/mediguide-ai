from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    supabase_url: str = ""
    supabase_anon_key: str = ""            # publishable key (safe for client use)
    supabase_service_role_key: str = ""    # server only: audit log, account deletion, admin
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    ocr_worker_url: str = ""               # if set, OCR is delegated to the Docker worker
    ocr_worker_token: str = ""             # shared secret between API and OCR worker
    max_upload_bytes: int = 20 * 1024 * 1024
    rate_limit_per_minute: int = 30
    allowed_origins: str = "http://localhost:3000"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

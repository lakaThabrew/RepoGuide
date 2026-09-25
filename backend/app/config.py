from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    github_token: str = ""
    ai_api_key: str = ""
    # Base URL for the AI inference endpoint (OpenAI-compatible).
    # For IBM Bob 2.0: set to the Bob inference base URL.
    # Defaults to official OpenAI endpoint if left empty.
    ai_base_url: str = ""
    # Model identifier to use for analysis (provider-specific).
    ai_model: str = "gpt-4o-mini"
    # Request timeout in seconds for AI calls.
    ai_timeout: int = 60
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

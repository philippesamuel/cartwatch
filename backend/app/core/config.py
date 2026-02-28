from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env() -> Path:
    for parent in Path(__file__).parents:
        env = parent / ".env"
        if env.exists():
            return env
    return Path(".env")  # fallback


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_find_env(), extra="ignore")

    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr
    anthropic_api_key: SecretStr | None = None
    environment: str = "development"
    gmail_label: str = "Kassenbons"


settings = Settings()  # ty: ignore[missing-argument]

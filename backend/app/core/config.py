from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils import find_env


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_env(), extra="ignore")

    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr
    supabase_user_id: str
    mistral_api_key: SecretStr
    # Gmail OAuth
    gmail_client_id: SecretStr
    gmail_client_secret: SecretStr
    gmail_refresh_token: SecretStr
    mistral_base_url: str = "https://api.mistral.ai"
    environment: str = "development"
    gmail_label: str = "Kassenbons"
    


settings = Settings()  # ty: ignore[missing-argument]

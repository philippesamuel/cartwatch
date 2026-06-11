from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils import find_env


class SupabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_env(), extra="ignore")
    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr
    supabase_user_id: str


class GmailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_env(), extra="ignore")
    # Gmail OAuth
    gmail_client_id: SecretStr
    gmail_client_secret: SecretStr
    gmail_refresh_token: SecretStr
    gmail_label: str = "Kassenbons"


class MistralSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_env(), extra="ignore")
    mistral_api_key: SecretStr
    mistral_base_url: str = "https://api.mistral.ai"
    

@lru_cache
def get_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings() # pyright: ignore[reportCallIssue]

@lru_cache
def get_gmail_settings() -> GmailSettings:
    return GmailSettings() # pyright: ignore[reportCallIssue]

@lru_cache
def get_mistral_settings() -> MistralSettings:
    return MistralSettings() # pyright: ignore[reportCallIssue]

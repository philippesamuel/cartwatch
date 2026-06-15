from supabase import Client, create_client

from core.config import get_supabase_settings


def get_supabase() -> Client:
    settings = get_supabase_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key.get_secret_value())

from supabase import create_client, Client
from app.core.config import settings

def get_supabase() -> Client:
    return create_client(settings.supabase_url, setting.supabase_service_key)


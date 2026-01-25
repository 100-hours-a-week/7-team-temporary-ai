from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

_client: Optional[Client] = None

def get_supabase_client() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("Supabase credentials not configured in settings")
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client

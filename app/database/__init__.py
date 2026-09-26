"""Database module initialization."""
from app.database.supabase_client import get_supabase, get_supabase_admin

__all__ = ["get_supabase", "get_supabase_admin"]

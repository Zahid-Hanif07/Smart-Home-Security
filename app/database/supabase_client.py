import os
from supabase import create_client, Client
from app.config.backend_settings import settings


class SupabaseClientManager:
    """Centralized Supabase Client Singleton Manager."""

    _instance: Client = None
    _admin_instance: Client = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or initialize standard Supabase client (Anon Key)."""
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_ANON_KEY,
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase anon client: {e}")
                cls._instance = None
        return cls._instance

    @classmethod
    def get_admin_client(cls) -> Client:
        """Get or initialize admin Supabase client (Service Role Key).

        SECURITY WARNING: Service Role Key is strictly server-side only.
        """
        if cls._admin_instance is None:
            try:
                cls._admin_instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY,
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase service role client: {e}")
                cls._admin_instance = None
        return cls._admin_instance


def get_supabase() -> Client:
    """Dependency helper to return standard Supabase client."""
    return SupabaseClientManager.get_client()


def get_supabase_admin() -> Client:
    """Dependency helper to return admin Supabase client."""
    return SupabaseClientManager.get_admin_client()

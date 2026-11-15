import os
import time
from typing import Optional
from uuid import UUID
import jwt

from app.config.backend_settings import settings
from app.database.supabase_client import SupabaseClientManager


def get_effective_auth_token(home_id: Optional[str] = None, explicit_token: Optional[str] = None) -> Optional[str]:
    """Return a valid authenticated token for local worker/publisher processes.

    Priority order:
    1. Returns explicit_token if provided and not expired.
    2. Returns SUPABASE_ACCESS_TOKEN from environment if configured and not expired.
    3. If SUPABASE_JWT_SECRET is set and home_id resolves to a real owner (via Supabase
       admin lookup or in-memory), mints a 30-day HS256 JWT for that owner.

    Returns None when no token can be produced with a verified owner identity.
    The caller must surface a clear error — never substitute a fabricated identity.
    """
    token = explicit_token or os.getenv("SUPABASE_ACCESS_TOKEN") or os.getenv("AUTH_TOKEN") or settings.SUPABASE_ACCESS_TOKEN
    if token:
        try:
            # Check if token is still valid (not expired)
            jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            return token
        except jwt.ExpiredSignatureError:
            pass  # Token expired, fall through to auto-generated owner token
        except Exception:
            return token

    # Auto-generate owner-scoped token if SUPABASE_JWT_SECRET is configured
    if not settings.SUPABASE_JWT_SECRET:
        return None

    owner_id: Optional[str] = None
    if home_id:
        try:
            # Attempt to lookup real home owner in Supabase
            admin = SupabaseClientManager.get_admin_client()
            if admin:
                res = admin.table("homes").select("owner_id").eq("id", str(home_id)).execute()
                if res.data and len(res.data) > 0:
                    owner_id = str(res.data[0]["owner_id"])
        except Exception:
            pass

        if not owner_id:
            # Check in-memory homes
            from app.repositories.home_repository import home_repository
            try:
                h_uuid = UUID(str(home_id))
                in_mem = home_repository._in_memory_homes.get(h_uuid)
                if in_mem:
                    owner_id = str(in_mem["owner_id"])
            except Exception:
                pass

    if not owner_id:
        # Cannot safely mint a token without a verified real owner identity.
        # Return None so the caller can surface a clear, actionable error
        # rather than using a fabricated sub that fails every ownership check.
        import logging
        logging.getLogger(__name__).warning(
            "Cannot resolve home owner for SECURITY_HOME_ID=%s. "
            "Set SUPABASE_ACCESS_TOKEN in .env, or ensure the home exists in the "
            "database and SUPABASE_SERVICE_ROLE_KEY is valid.",
            home_id,
        )
        return None

    now = int(time.time())
    payload = {
        "sub": str(owner_id),
        "id": str(owner_id),
        "email": f"worker_{str(owner_id)[:8]}@internal.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": now + 86400 * 30,  # 30 days
        "iat": now,
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

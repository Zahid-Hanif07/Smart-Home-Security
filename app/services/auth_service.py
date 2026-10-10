import jwt
from typing import Dict, Any
from fastapi import HTTPException, status
from app.config.backend_settings import settings
from app.database.supabase_client import SupabaseClientManager


def is_supabase_configured() -> bool:
    """Check whether real Supabase credentials are configured in environment."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_ANON_KEY
    if not url or "demo-project" in url or "your-project-id" in url:
        return False
    if not key or "dummy" in key or "your-supabase" in key:
        return False
    return True


class AuthService:
    """Authentication service for verifying Supabase JWT tokens strictly with signature verification."""

    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Decode and verify incoming Supabase Bearer JWT token.

        Supports both real Supabase Auth tokens (ES256/RS256/HS256) via Supabase API
        and unit test mock tokens via PyJWT.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 1. Primary: Verify real Supabase Auth token via Supabase Auth API
        if is_supabase_configured():
            client = SupabaseClientManager.get_client()
            if client:
                try:
                    res = client.auth.get_user(jwt=token)
                    if res and res.user:
                        user = res.user
                        return {
                            "sub": str(user.id),
                            "id": str(user.id),
                            "email": user.email or "",
                            "user_metadata": user.user_metadata or {},
                        }
                except HTTPException:
                    raise
                except Exception:
                    # If Supabase API lookup fails (e.g. mock test token or network issue), fall through to PyJWT fallback
                    pass

        # 2. Fallback: PyJWT decoding for offline/unit test tokens
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token signature.",
                headers={"WWW-Authenticate": "Bearer"},
            )


import jwt
from typing import Dict, Any
from fastapi import HTTPException, status
from app.config.backend_settings import settings


class AuthService:
    """Authentication service for verifying Supabase JWT tokens strictly with signature verification."""

    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Decode and verify incoming Supabase Bearer JWT token.

        Args:
            token (str): JWT Bearer token string.

        Returns:
            Dict[str, Any]: Decoded token payload dictionary containing 'sub' (User UUID) and 'email'.

        Raises:
            HTTPException: 401 Unauthorized if token is invalid, expired, or unverified.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Strict signature verification with SUPABASE_JWT_SECRET
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

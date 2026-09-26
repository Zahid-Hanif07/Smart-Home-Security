from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from app.services.auth_service import AuthService
from app.database.supabase_client import get_supabase, get_supabase_admin


def get_token_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract Bearer token string from HTTP Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


def get_current_user(token: str = Depends(get_token_header)) -> Dict[str, Any]:
    """Dependency returning authenticated user claims dictionary."""
    payload = AuthService.verify_jwt_token(token)
    user_id_str = payload.get("sub") or payload.get("id")

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject user ID.",
        )

    try:
        user_uuid = UUID(str(user_id_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid UUID format in user token.",
        )

    return {
        "id": user_uuid,
        "email": payload.get("email", "user@example.com"),
        "name": payload.get("user_metadata", {}).get("name", payload.get("email", "User")),
    }


def get_current_user_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> UUID:
    """Dependency returning authenticated user's UUID."""
    return current_user["id"]

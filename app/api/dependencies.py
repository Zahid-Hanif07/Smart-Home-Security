"""FastAPI dependency functions for user and device authentication.

User authentication
-------------------
``get_current_user`` / ``get_current_user_id`` — validate a Supabase Bearer
JWT and return the authenticated user's claims or UUID.

Device authentication (Phase 3A)
---------------------------------
``get_authenticated_device`` — validate an opaque device credential issued
during the pairing claim flow.  Uses ``Authorization: DeviceToken <token>``
(a distinct scheme from ``Bearer``) to prevent accidental token confusion.

Security note: NEVER log the Authorization header value in either function.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from app.services.auth_service import AuthService
from app.database.supabase_client import get_supabase, get_supabase_admin


_DEVICE_SESSION_AUTH_FAILURE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Device session authentication failed.",
    headers={"WWW-Authenticate": "DeviceSession"},
)


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


# ---------------------------------------------------------------------------
# Phase 3A — Device authentication dependency
# ---------------------------------------------------------------------------

# Single reusable exception for ALL device-auth failures.
# Using the same message for every failure mode (no device found, wrong
# token, revoked device) prevents callers from distinguishing whether a
# device_id is valid — this limits enumeration attacks.
_DEVICE_AUTH_FAILURE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Device authentication failed.",
    headers={"WWW-Authenticate": "DeviceToken"},
)


def get_authenticated_device(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Dependency for endpoints that require a device credential.

    Validates an ``Authorization: DeviceToken <token>`` header where
    ``<token>`` is the opaque value returned by ``POST /api/pairing/claim``
    (present only on first registration).

    Auth flow:
      1. Parse the ``DeviceToken`` scheme (distinct from ``Bearer``).
      2. Split the token into device_id prefix + secret portion.
      3. Fetch the device record by primary key (one DB read).
      4. Verify the secret against the stored bcrypt hash.
      5. Confirm the device has not been revoked.

    Returns a dict with keys: ``device_id`` (UUID), ``home_id`` (UUID).

    Raises:
        HTTPException 401 — for ANY auth failure.  The detail message is
            intentionally generic to avoid leaking device existence.

    SECURITY: The authorization header value MUST NOT be logged.
    """
    if not authorization:
        raise _DEVICE_AUTH_FAILURE

    # Split on the first whitespace only (token may not contain spaces,
    # but splitting once is safer than split()).
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "devicetoken":
        raise _DEVICE_AUTH_FAILURE

    raw_token = parts[1]

    # Parse token format: dvc_<uuid_hex>_<64_hex_chars>
    from app.security.device_credential import parse_token, verify_token_secret
    try:
        device_id, secret = parse_token(raw_token)
    except ValueError:
        raise _DEVICE_AUTH_FAILURE

    # Primary-key lookup — no user ownership check here.
    from app.repositories.device_repository import device_repository
    try:
        device = device_repository.get_device_by_id_unchecked(device_id)
    except HTTPException:
        # DB errors are surfaced as 401 to avoid leaking infrastructure state
        # to potentially unauthenticated callers.
        raise _DEVICE_AUTH_FAILURE

    if device is None:
        raise _DEVICE_AUTH_FAILURE

    credential_hash = device.get("credential_hash")
    if not credential_hash:
        # Device has no credential (was revoked, or never completed pairing).
        raise _DEVICE_AUTH_FAILURE

    # Constant-time bcrypt verify.
    if not verify_token_secret(secret, credential_hash):
        raise _DEVICE_AUTH_FAILURE

    # Check revocation status AFTER bcrypt verify to avoid timing oracles
    # that would distinguish "wrong token" from "revoked device".
    if device.get("status") == "revoked":
        raise _DEVICE_AUTH_FAILURE

    return {
        "device_id": device["id"],
        "home_id": device["home_id"],
        "status": device.get("status", "offline"),
    }


def get_authenticated_device_session(
    authorization: Optional[str] = Header(None),
    x_home_id: UUID = Header(..., alias="X-Home-ID"),
) -> Dict[str, Any]:
    """Validate a signed, current device session bound to ``X-Home-ID``."""
    parts = authorization.split(None, 1) if authorization else []
    if len(parts) != 2 or parts[0].lower() != "devicesession":
        raise _DEVICE_SESSION_AUTH_FAILURE

    from app.security.device_session_token import validate_device_session_token
    from app.repositories.device_repository import device_repository

    try:
        claims = validate_device_session_token(
            parts[1],
            expected_home_id=x_home_id,
        )
        device_id = UUID(str(claims["device_id"]))
        device_state = device_repository.get_device_session_state(device_id)
    except (ValueError, KeyError):
        raise _DEVICE_SESSION_AUTH_FAILURE
    except HTTPException as exc:
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=503,
                detail="Device session status is temporarily unavailable.",
            ) from exc
        raise _DEVICE_SESSION_AUTH_FAILURE

    if (
        device_state is None
        or str(device_state.get("status", "")).lower() == "revoked"
        or device_state.get("home_id") != x_home_id
    ):
        raise _DEVICE_SESSION_AUTH_FAILURE

    return {"device_id": device_id, "home_id": x_home_id}

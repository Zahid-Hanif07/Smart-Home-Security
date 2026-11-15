"""Short-lived signed sessions for already-authenticated desktop devices.

This module only issues and validates session JWTs. Device-credential
authentication and session exchange belong to a separate API flow.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any
from uuid import UUID

import jwt

from app.config.backend_settings import settings

DEVICE_SESSION_ALGORITHM = "HS256"
DEVICE_SESSION_ISSUER = "smart-home-security"
DEVICE_SESSION_AUDIENCE = "smart-home-security-device-session"
DEVICE_SESSION_MAX_LIFETIME_SECONDS = 60
_REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub", "device_id", "home_id", "jti"]
_MIN_SIGNING_SECRET_BYTES = 32


def _get_signing_secret() -> str:
    """Return the dedicated server-side key, failing closed if unconfigured."""
    secret = settings.DEVICE_SESSION_SIGNING_SECRET
    if not secret or len(secret.encode("utf-8")) < _MIN_SIGNING_SECRET_BYTES:
        raise ValueError(
            "Device session signing is not configured. Set DEVICE_SESSION_SIGNING_SECRET "
            "to a dedicated random secret of at least 32 bytes."
        )
    return secret


def create_device_session_token(
    *,
    device_id: UUID,
    home_id: UUID,
    lifetime_seconds: int = DEVICE_SESSION_MAX_LIFETIME_SECONDS,
    now: datetime | None = None,
) -> str:
    """Create a signed session from server-resolved device and home IDs.

    Callers must pass IDs obtained from authenticated server-side device
    lookup, never values accepted from the device as proof of ownership.
    """
    if not 1 <= lifetime_seconds <= DEVICE_SESSION_MAX_LIFETIME_SECONDS:
        raise ValueError("Device session lifetime must be between 1 and 60 seconds.")

    issued_at = now or datetime.now(timezone.utc)
    if issued_at.tzinfo is None:
        raise ValueError("Device session issue time must be timezone-aware.")
    issued_at = issued_at.astimezone(timezone.utc)
    issued_timestamp = int(issued_at.timestamp())
    claims = {
        "iss": DEVICE_SESSION_ISSUER,
        "aud": DEVICE_SESSION_AUDIENCE,
        "sub": str(device_id),
        "device_id": str(device_id),
        "home_id": str(home_id),
        "iat": issued_timestamp,
        "exp": issued_timestamp + lifetime_seconds,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        claims,
        _get_signing_secret(),
        algorithm=DEVICE_SESSION_ALGORITHM,
        headers={"typ": "JWT"},
    )


def validate_device_session_token(
    token: str,
    *,
    expected_device_id: UUID | None = None,
    expected_home_id: UUID,
) -> dict[str, Any]:
    """Verify a session JWT and its binding to the expected device and home.

    This validator performs signature/claim checks only. It never looks up or
    verifies a bcrypt device credential.
    """
    if not isinstance(token, str) or not token:
        raise ValueError("Invalid device session token.")

    signing_secret = _get_signing_secret()
    try:
        claims = jwt.decode(
            token,
            signing_secret,
            algorithms=[DEVICE_SESSION_ALGORITHM],
            issuer=DEVICE_SESSION_ISSUER,
            audience=DEVICE_SESSION_AUDIENCE,
            options={"require": _REQUIRED_CLAIMS},
        )
        device_id = UUID(str(claims["device_id"]))
        subject_id = UUID(str(claims["sub"]))
        home_id = UUID(str(claims["home_id"]))
        if (
            device_id != subject_id
            or (expected_device_id is not None and device_id != expected_device_id)
            or home_id != expected_home_id
        ):
            raise ValueError("Invalid device session token.")
        if not isinstance(claims["jti"], str) or not claims["jti"]:
            raise ValueError("Invalid device session token.")
        issued_at = claims["iat"]
        expires_at = claims["exp"]
        if isinstance(issued_at, bool) or not isinstance(issued_at, (int, float)):
            raise ValueError("Invalid device session token.")
        if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
            raise ValueError("Invalid device session token.")
        if expires_at <= issued_at or expires_at - issued_at > DEVICE_SESSION_MAX_LIFETIME_SECONDS:
            raise ValueError("Invalid device session token.")
        return claims
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError) as exc:
        # Do not include token contents or signing configuration in failures.
        raise ValueError("Invalid device session token.") from exc

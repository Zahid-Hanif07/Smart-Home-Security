"""Device credential generation, hashing, and verification — Phase 3A.

Security design
---------------
Token wire format:  ``dvc_<device_uuid_hex>_<64_hex_chars>``

  * ``dvc_`` — fixed 4-char prefix, distinguishes device tokens from
    Supabase user JWTs at a glance (and in logs if the token is ever
    accidentally printed — the value will still be partially visible but
    the prefix makes the leak obvious).
  * ``<device_uuid_hex>`` — 32 hex characters (UUID without hyphens).
    Allows the auth dependency to perform a **single primary-key lookup**
    before the expensive bcrypt verify step.  Including the device ID in
    the token is safe because device IDs are not secret — they are
    returned in claim responses and visible to home owners.
  * ``<64_hex_chars>`` — output of ``secrets.token_hex(32)`` (256 bits of
    entropy).  This is the *secret portion* — the only part verified against
    the stored hash.

Storage:
  Only the bcrypt hash of the secret portion (the 64 hex chars) is persisted
  in the ``devices.credential_hash`` column.  The raw token and raw secret are
  **never written to any log, database column, or response body** after the
  one-time claim issuance.

Bcrypt implementation:
  Uses the ``bcrypt`` library directly (not via passlib) to avoid the passlib
  1.7.4 / bcrypt 4.x+ incompatibility where passlib's ``detect_wrap_bug``
  test causes a ValueError on Python 3.14.  The bcrypt library's own API is
  stable and does not have this issue.

  Cost factor: 12 (~250 ms per hash on a typical server).  This is
  intentionally slow for offline dictionary attacks against a leaked DB.
  NOTE for Phase 3B: per-frame endpoints must NOT re-verify bcrypt on every
  frame; use a short-lived session token derived from this credential instead.

CRITICAL: Never log the raw token or the Authorization header value.
"""
from __future__ import annotations

import re
import secrets
from uuid import UUID

import bcrypt

# bcrypt cost factor 12
_BCRYPT_ROUNDS = 12

# Fixed-length pattern: "dvc_" + 32 hex UUID chars + "_" + 64 hex secret chars.
# Total token length: 3 (prefix) + 1 (_) + 32 (UUID hex) + 1 (_) + 64 (secret hex) = 101 characters.
_TOKEN_RE = re.compile(r"^dvc_([0-9a-f]{32})_([0-9a-f]{64})$")

TOKEN_PREFIX = "dvc"
TOKEN_LENGTH = 101  # 3 (prefix) + 1 (_) + 32 (UUID hex) + 1 (_) + 64 (secret hex) = 101


def generate_raw_token(device_id: UUID) -> str:
    """Return a new raw device credential token.

    The returned value is the ONLY time the raw token exists in plaintext.
    Callers MUST:
    - Return it to the device exactly once (in the claim response body).
    - Immediately hash it with :func:`hash_token_secret` before storing.
    - NEVER log it, cache it, or write it to any persistent store.

    Args:
        device_id: The UUID of the device this token belongs to.  The hex
            representation is embedded in the token prefix so that the auth
            dependency can look up the device with a single primary-key query.

    Returns:
        A 101-character opaque token string.
    """
    return f"{TOKEN_PREFIX}_{device_id.hex}_{secrets.token_hex(32)}"


def hash_token_secret(secret: str) -> str:
    """Return a bcrypt hash of the secret portion of a device token.

    Store the returned value in ``devices.credential_hash``.  The raw
    ``secret`` must be discarded immediately after this call.

    Args:
        secret: The 64-character hex secret extracted by :func:`parse_token`.

    Returns:
        A bcrypt hash string safe for database storage.
    """
    # bcrypt requires bytes; encode to UTF-8.
    # 64 hex chars = 64 bytes — well within bcrypt's 72-byte limit.
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(secret.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_token_secret(secret: str, stored_hash: str) -> bool:
    """Constant-time verification of a secret against a stored bcrypt hash.

    Returns ``True`` only if ``secret`` matches ``stored_hash``.  Any
    exception (invalid hash format, bcrypt error) is caught and treated as
    a failed verification to avoid leaking information.

    Args:
        secret: The 64-character hex secret extracted by :func:`parse_token`.
        stored_hash: The bcrypt hash from ``devices.credential_hash``.

    Returns:
        ``True`` if the secret is valid; ``False`` otherwise.
    """
    try:
        return bcrypt.checkpw(secret.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


def parse_token(token: str) -> tuple[UUID, str]:
    """Parse a raw device token into ``(device_id, secret_portion)``.

    The ``secret_portion`` (64 hex chars) is what gets hashed and verified.
    The ``device_id`` is used only for the primary-key DB lookup.

    Args:
        token: The raw token string from an ``Authorization: DeviceToken …``
            header (or directly from the claim response in tests).

    Returns:
        A ``(UUID, str)`` tuple: the device's UUID and the secret portion.

    Raises:
        ValueError: If the token does not match the expected format.  The
            error message is intentionally generic to avoid leaking structure
            to attackers.
    """
    m = _TOKEN_RE.match(token or "")
    if not m:
        raise ValueError("Invalid device token format.")
    device_id = UUID(m.group(1))
    secret = m.group(2)
    return device_id, secret

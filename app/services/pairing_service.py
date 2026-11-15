"""PairingService: business logic for pairing-code lifecycle.

Responsibilities
----------------
* Generate cryptographically secure, human-friendly codes.
* Enforce rate limits (max active codes per home).
* Compute expiry.
* Delegate persistence to PairingRepository.
* Issue a one-time device credential after a successful pairing claim
  (Phase 3A).

Code format
-----------
Six uppercase alphanumeric characters from a 32-character alphabet that
excludes visually ambiguous characters (0/O, 1/I, 5/S, 8/B).
Example: ``A3F72K``  displayed as ``A3F-72K`` in the UI.

Entropy: 26^6 ≈ 309 million distinct codes with a 5-minute window → collision
probability is negligible for the single-home, single-session use case.

Device credential (Phase 3A)
------------------------------
After a successful claim, ``claim_code()`` issues an opaque device token.
The token is returned in the response body exactly once — it is not stored
raw anywhere.  Only the bcrypt hash of the token's secret portion is
persisted to ``devices.credential_hash``.

NEVER log the raw device_token or any Authorization header value.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.pairing_repository import PairingRepository, pairing_repository

# Alphabet: uppercase letters + digits, minus 0/O, 1/I, 5/S, 8/B
_CODE_ALPHABET = "ACDEFGHJKLMNPQRTUVWXYZ2346789"

# Code length and display separator position
_CODE_LENGTH = 6
_CODE_TTL_SECONDS = 300  # 5 minutes


def _generate_code() -> str:
    """Return a 6-character code from the unambiguous alphabet."""
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


class PairingService:
    """Orchestrates pairing-code creation and claim validation."""

    def __init__(self, repository: PairingRepository | None = None) -> None:
        self._repo = repository or pairing_repository

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def generate_code(
        self,
        home_id: UUID,
        requesting_user_id: UUID,
    ) -> Dict[str, Any]:
        """Create and persist a new pairing code for ``home_id``.

        Args:
            home_id: The home this code will grant streaming access to.
            requesting_user_id: The authenticated user making the request.
                Ownership of ``home_id`` must be verified by the caller
                (the route depends on ``get_current_user_id`` + the home
                repository ownership check which is done in the route layer).

        Returns:
            A dict with keys: code, home_id, expires_at, ttl_seconds.

        Raises:
            HTTPException 429 — too many active codes for this home.
            HTTPException 500 — persistence failure.
        """
        # Rate-limit: no more than MAX_ACTIVE_CODES_PER_HOME simultaneously
        active_count = self._repo.count_active_codes(home_id)
        if active_count >= self._repo.MAX_ACTIVE_CODES_PER_HOME:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"This home already has {active_count} active pairing code(s). "
                    "Wait for them to expire or use an existing code before generating a new one."
                ),
            )

        # Generate with uniqueness retry (probability of collision is ~1 in 309M,
        # but we try up to 5 times to be safe in the extremely unlikely event of a
        # UNIQUE constraint violation).
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=_CODE_TTL_SECONDS)
        code: str | None = None
        record: Dict[str, Any] | None = None

        for _ in range(5):
            candidate = _generate_code()
            try:
                record = self._repo.create_code(
                    home_id=home_id,
                    code=candidate,
                    expires_at=expires_at,
                )
                code = candidate
                break
            except HTTPException as exc:
                # 500 from a UNIQUE violation on the code column — retry.
                if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR and "unique" in str(exc.detail).lower():
                    continue
                raise

        if record is None or code is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate a unique pairing code after multiple attempts. Please try again.",
            )

        # Format with separator for display
        display_code = f"{code[:3]}-{code[3:]}"
        remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())

        return {
            "code": display_code,
            "home_id": home_id,
            "expires_at": expires_at,
            "ttl_seconds": max(0, remaining),
        }

    # ------------------------------------------------------------------
    # Claim (Phase 3A: issues a device credential on new registration)
    # ------------------------------------------------------------------

    def claim_code(
        self,
        code: str,
        device_name: str,
        device_type: str,
        device_identifier: str,
    ) -> Dict[str, Any]:
        """Validate and atomically consume a pairing code; register the device.

        After registering a NEW device, issues a one-time opaque credential
        token.  The token is embedded in the returned dict as ``device_token``
        and persisted only as a bcrypt hash in ``devices.credential_hash``.

        For an ALREADY REGISTERED device (same device_identifier + same home),
        no new token is issued.  ``credential_already_issued=True`` is returned
        instead.  To obtain a fresh token, the home owner must revoke the
        device and re-pair.

        ``code`` arrives already normalised (hyphen stripped, uppercase) by
        the Pydantic model validator.

        The home_id is derived exclusively from the persisted code record —
        the desktop cannot supply or override it.

        SECURITY: The raw ``device_token`` must never be logged by callers.
        """
        # Deferred imports: avoid circular import at module level
        # (pairing_service → device_repository → home_repository → OK).
        from app.repositories.device_repository import device_repository
        from app.security.device_credential import (
            generate_raw_token,
            hash_token_secret,
            parse_token,
        )

        result = self._repo.claim_code(
            code=code,
            device_name=device_name,
            device_type=device_type,
            device_identifier=device_identifier,
        )

        device_id: UUID = result["device_id"]

        if result["status"] == "registered":
            # New device — issue a fresh credential exactly once.
            raw_token = generate_raw_token(device_id)
            # parse_token extracts only the secret portion (64 hex chars)
            # that gets hashed.  The device_id prefix is NOT hashed.
            _, secret = parse_token(raw_token)
            hashed = hash_token_secret(secret)

            # Persist the bcrypt hash.  Raises 500 on failure so we never
            # silently return a token whose hash was not stored.
            device_repository.store_credential_hash(device_id, hashed)

            result["device_token"] = raw_token
            result["credential_already_issued"] = False

        else:
            # Already registered — do not issue or re-issue a credential.
            # The operator must revoke + re-pair to obtain a new token.
            result["device_token"] = None
            result["credential_already_issued"] = True

        return result


# Module-level singleton
pairing_service = PairingService()

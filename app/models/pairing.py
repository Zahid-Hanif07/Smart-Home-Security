"""Pydantic models for the desktop-pairing flow.

Pairing codes are short-lived, cryptographically random tokens that let an
authenticated home owner authorise a specific desktop to stream camera frames
for their home.  The claim body comes from an unauthenticated desktop caller,
so every field is validated strictly to avoid injection or type-confusion.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Code-generation response (returned to the authenticated mobile/web caller)
# ---------------------------------------------------------------------------

class PairingCodeResponse(BaseModel):
    """Response body for POST /api/homes/{home_id}/pairing-codes."""

    code: str = Field(description="Human-readable one-time pairing code (e.g. 'A3F-72K').")
    home_id: UUID = Field(description="The home this code grants access to.")
    expires_at: datetime = Field(description="UTC timestamp when this code expires.")
    ttl_seconds: int = Field(description="Remaining lifetime in seconds at the time of creation.")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Claim request (sent from the unauthenticated desktop caller)
# ---------------------------------------------------------------------------

# Regex: exactly the 6-character format produced by the code generator (e.g. A3F72K).
# Hyphens are optional to accommodate copy-paste from QR vs. manual entry.
_CODE_RE = re.compile(r"^[A-Z0-9]{3}-?[A-Z0-9]{3}$")

# Regex: alphanumeric + hyphens, 1-128 chars — suitable for a machine/app UUID.
_DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,128}$")


class PairingClaimRequest(BaseModel):
    """Request body for POST /api/pairing/claim.

    All fields come from the desktop; none is trusted for ownership decisions.
    The home is resolved exclusively from the persisted code record.
    """

    code: str = Field(
        description="The one-time pairing code shown to the home owner.",
        min_length=6,
        max_length=7,  # allows optional hyphen (e.g. 'A3F-72K')
    )
    device_name: str = Field(
        description="Human-readable label for this desktop (e.g. 'Living Room PC').",
        min_length=1,
        max_length=100,
    )
    device_type: str = Field(
        default="desktop_camera",
        description="Category of this device.",
        min_length=1,
        max_length=60,
    )
    device_identifier: str = Field(
        description="Stable machine-unique identifier (e.g. UUID derived from hardware).",
        min_length=1,
        max_length=128,
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not _CODE_RE.match(cleaned):
            raise ValueError("Pairing code must be exactly 6 alphanumeric characters (e.g. 'A3F72K' or 'A3F-72K').")
        # Normalise: strip any hyphen for storage/lookup
        return cleaned.replace("-", "")

    @field_validator("device_identifier")
    @classmethod
    def validate_device_identifier(cls, value: str) -> str:
        stripped = value.strip()
        if not _DEVICE_ID_RE.match(stripped):
            raise ValueError("device_identifier may only contain alphanumeric characters and hyphens.")
        return stripped

    @field_validator("device_name")
    @classmethod
    def validate_device_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("device_name must not be blank.")
        return stripped

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, value: str) -> str:
        allowed = {
            "desktop_camera",
            "laptop_camera",
            "server_camera",
            "raspberry_pi",
            "embedded_camera",
        }
        cleaned = value.strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"device_type must be one of: {', '.join(sorted(allowed))}.")
        return cleaned


# ---------------------------------------------------------------------------
# Claim response (Phase 3A: includes one-time device credential)
# ---------------------------------------------------------------------------

class PairingClaimResponse(BaseModel):
    """Successful claim response — Phase 3A.

    ``device_token`` is present ONLY on the first successful registration
    (``status == 'registered'``).  It will NOT be returned on subsequent
    claims for the same device identifier on the same home.

    Security notes for the caller:
    - Store ``device_token`` in a secure, OS-level credential store.
    - NEVER log this value or transmit it over an unencrypted channel.
    - Present it as ``Authorization: DeviceToken <device_token>`` on
      device-authenticated endpoints.
    - There is no refresh or re-issuance endpoint — to obtain a new token
      the home owner must revoke the device and re-pair.
    """

    device_id: UUID = Field(description="Newly registered (or pre-existing) device UUID.")
    home_id: UUID = Field(description="The home this device is now bound to.")
    device_name: str
    device_type: str
    status: str = Field(description="'registered' or 'already_registered'.")
    message: str
    device_token: Optional[str] = Field(
        default=None,
        description=(
            "Opaque one-time device credential. Present only on first registration. "
            "Store securely — it will not be returned again."
        ),
    )
    credential_already_issued: bool = Field(
        default=False,
        description=(
            "True when this device_identifier was already registered and its credential "
            "was previously issued. No new token is returned in this case."
        ),
    )

    model_config = ConfigDict(from_attributes=True)

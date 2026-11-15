"""FastAPI routes for device CRUD and Phase 3A device authentication operations.

Endpoints
---------
User-authenticated (Bearer JWT):
  POST   /api/homes/{home_id}/devices          — register a device
  GET    /api/homes/{home_id}/devices          — list devices for a home
  PUT    /api/devices/{device_id}              — update device metadata
  DELETE /api/devices/{device_id}             — delete a device
  POST   /api/devices/{device_id}/revoke      — revoke device credential (Phase 3A)

Device-authenticated (DeviceToken):
  GET    /api/devices/me                       — heartbeat / self-info (Phase 3A)
  POST   /api/devices/session                  — exchange/renew a short-lived device session (Phase 3B.2)

Phase 3A security notes
-----------------------
* ``/revoke`` requires the home owner's Bearer JWT — a device cannot
  revoke itself.
* ``/me`` requires the device's own DeviceToken credential, allowing the
  desktop to verify its token is still valid before beginning an operation.
* Revocation takes effect immediately; the next request from the device
  will be rejected by ``get_authenticated_device``.
"""
from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import get_current_user_id, get_authenticated_device
from app.models.device import DeviceCreate, DeviceUpdate, DeviceResponse
from app.repositories.device_repository import device_repository
from app.security.device_session_token import (
    DEVICE_SESSION_MAX_LIFETIME_SECONDS,
    create_device_session_token,
)
from app.services.backend_store import backend_store

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing user-authenticated CRUD routes (unchanged behaviour)
# ---------------------------------------------------------------------------

@router.post("/homes/{home_id}/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    home_id: UUID,
    data: DeviceCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Register a security device (camera, esp32, door controller) to a home."""
    return backend_store.create_device(home_id=home_id, requesting_user_id=user_id, data=data)


@router.get("/homes/{home_id}/devices", response_model=List[DeviceResponse])
def get_home_devices(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all security devices belonging to a home."""
    return backend_store.get_home_devices(home_id=home_id, requesting_user_id=user_id)


@router.put("/devices/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: UUID,
    data: DeviceUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Update device metadata, status, or last_seen timestamp."""
    return backend_store.update_device(device_id=device_id, requesting_user_id=user_id, data=data)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a registered device."""
    backend_store.delete_device(device_id=device_id, requesting_user_id=user_id)
    return None


# ---------------------------------------------------------------------------
# Phase 3A — Credential revocation (user-authenticated)
# ---------------------------------------------------------------------------

@router.post(
    "/devices/{device_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a device's credential",
    description=(
        "Clears the device's credential hash and sets its status to 'revoked'. "
        "The device will be rejected on its next authenticated request. "
        "Requires the home owner's Bearer JWT — devices cannot revoke themselves. "
        "To re-enable the device, delete it and re-pair."
    ),
    tags=["Devices"],
)
def revoke_device(
    device_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """POST /api/devices/{device_id}/revoke

    Owner-authenticated.  Revokes the device's opaque credential immediately.
    Returns 204 No Content on success.
    Returns 404 if the device does not exist.
    Returns 403 if the requesting user does not own the device's home.
    """
    device_repository.revoke_device(device_id=device_id, requesting_user_id=user_id)
    return None


# ---------------------------------------------------------------------------
# Phase 3A — Device self-info (device-authenticated)
# ---------------------------------------------------------------------------

@router.get(
    "/devices/me",
    summary="Device heartbeat / self-info",
    description=(
        "Called by the desktop application to verify its device credential is "
        "still valid and retrieve its server-assigned home_id. "
        "Requires Authorization: DeviceToken <token>."
    ),
    tags=["Devices"],
)
def get_device_me(
    device_info: Dict[str, Any] = Depends(get_authenticated_device),
):
    """GET /api/devices/me

    Device-authenticated.  Returns the device's own ``device_id``,
    ``home_id``, and ``status``.  Useful as a pre-flight check before
    beginning streaming operations.
    """
    return {
        "device_id": str(device_info["device_id"]),
        "home_id": str(device_info["home_id"]),
        "status": device_info["status"],
    }


# ---------------------------------------------------------------------------
# Phase 3B.2 — Device credential exchange and renewal
# ---------------------------------------------------------------------------

@router.post(
    "/devices/session",
    summary="Exchange or renew a short-lived device session",
    description=(
        "Requires the device's DeviceToken credential. Every call revalidates "
        "the stored credential hash and current device status, then returns a "
        "signed session lasting at most 60 seconds. The device and home claims "
        "are taken from the server-side device record."
    ),
)
def exchange_device_session(
    device_info: Dict[str, Any] = Depends(get_authenticated_device),
):
    """Issue or renew a device session from current authenticated device data."""
    try:
        session_token = create_device_session_token(
            device_id=device_info["device_id"],
            home_id=device_info["home_id"],
            lifetime_seconds=DEVICE_SESSION_MAX_LIFETIME_SECONDS,
        )
    except ValueError as exc:
        # Do not expose signing configuration values or token material.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device session signing is not configured.",
        ) from exc

    return {
        "session_token": session_token,
        "token_type": "DeviceSession",
        "expires_in": DEVICE_SESSION_MAX_LIFETIME_SECONDS,
        "home_id": str(device_info["home_id"]),
    }

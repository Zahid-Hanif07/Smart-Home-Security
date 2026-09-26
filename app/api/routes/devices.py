from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user_id
from app.models.device import DeviceCreate, DeviceUpdate, DeviceResponse
from app.services.backend_store import backend_store

router = APIRouter()


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

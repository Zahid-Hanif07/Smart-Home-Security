from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user_id
from app.models.home import HomeCreate, HomeUpdate, HomeResponse
from app.services.backend_store import backend_store

router = APIRouter()


@router.post("", response_model=HomeResponse, status_code=status.HTTP_201_CREATED)
def create_home(
    data: HomeCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new home owned by the authenticated user."""
    return backend_store.create_home(owner_id=user_id, data=data)


@router.get("", response_model=List[HomeResponse])
def get_user_homes(
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all homes owned by the authenticated user."""
    return backend_store.get_user_homes(owner_id=user_id)


@router.get("/{home_id}", response_model=HomeResponse)
def get_home_by_id(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve a single home owned by the authenticated user."""
    return backend_store.get_home_by_id(home_id=home_id, requesting_user_id=user_id)


@router.put("/{home_id}", response_model=HomeResponse)
def update_home(
    home_id: UUID,
    data: HomeUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Update details of a home owned by the authenticated user."""
    return backend_store.update_home(home_id=home_id, requesting_user_id=user_id, data=data)


@router.delete("/{home_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_home(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a home owned by the authenticated user."""
    backend_store.delete_home(home_id=home_id, requesting_user_id=user_id)
    return None

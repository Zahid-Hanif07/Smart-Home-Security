from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user
from app.models.user import ProfileResponse, ProfileUpdate
from app.services.backend_store import backend_store

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
def get_current_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    profile = backend_store.get_or_create_profile(
        user_id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
    )
    return profile


@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
def update_profile(
    update_data: ProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update profile details for currently authenticated user."""
    backend_store.get_or_create_profile(
        user_id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
    )
    updated_profile = backend_store.update_profile(current_user["id"], update_data)
    return updated_profile

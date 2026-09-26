from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user_id
from app.models.member import MemberCreate, MemberUpdate, MemberResponse
from app.services.backend_store import backend_store

router = APIRouter()


@router.post("/homes/{home_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_home_member(
    home_id: UUID,
    data: MemberCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Add an authorized family member/person to a home owned by the authenticated user."""
    return backend_store.create_member(home_id=home_id, requesting_user_id=user_id, data=data)


@router.get("/homes/{home_id}/members", response_model=List[MemberResponse])
def get_home_members(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all authorized members of a home owned by the authenticated user."""
    return backend_store.get_home_members(home_id=home_id, requesting_user_id=user_id)


@router.put("/members/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: UUID,
    data: MemberUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Update details of a home member."""
    return backend_store.update_member(member_id=member_id, requesting_user_id=user_id, data=data)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a home member."""
    backend_store.delete_member(member_id=member_id, requesting_user_id=user_id)
    return None

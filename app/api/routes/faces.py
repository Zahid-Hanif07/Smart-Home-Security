from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user_id
from app.models.face import FaceCreate, FaceResponse
from app.services.backend_store import backend_store

router = APIRouter()


@router.post("/members/{member_id}/faces", response_model=FaceResponse, status_code=status.HTTP_201_CREATED)
def create_face_record(
    member_id: UUID,
    data: FaceCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Store face record metadata & embedding for a home member."""
    return backend_store.create_face_record(member_id=member_id, requesting_user_id=user_id, data=data)


@router.get("/members/{member_id}/faces", response_model=List[FaceResponse])
def get_member_faces(
    member_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all face records belonging to a home member."""
    return backend_store.get_member_faces(member_id=member_id, requesting_user_id=user_id)


@router.delete("/faces/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_face_record(
    face_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a face record."""
    backend_store.delete_face_record(face_id=face_id, requesting_user_id=user_id)
    return None

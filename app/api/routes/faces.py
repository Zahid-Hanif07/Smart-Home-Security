import base64
from typing import List, Optional, Any, Dict
from uuid import UUID
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.dependencies import get_current_user_id
from app.models.face import FaceCreate, FaceResponse
from app.services.backend_store import backend_store
from app.security.face_detection_service import FaceDetectionService
from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_database import FaceDatabase

router = APIRouter()

# Singletons for SFace pipeline reuse
_detector: Optional[FaceDetectionService] = None
_embedder: Optional[FaceEmbeddingService] = None
_face_db: Optional[FaceDatabase] = None


def get_face_services():
    global _detector, _embedder, _face_db
    if _detector is None:
        _detector = FaceDetectionService()
    if _embedder is None:
        _embedder = FaceEmbeddingService()
    if _face_db is None:
        _face_db = FaceDatabase()
    return _detector, _embedder, _face_db


class FaceRegisterRequest(BaseModel):
    image_base64: Optional[str] = None
    image_path: Optional[str] = None
    embedding: Optional[List[float]] = None
    sample_count: Optional[int] = 1


@router.post("/members/{member_id}/faces", response_model=FaceResponse, status_code=status.HTTP_201_CREATED)
def create_face_record(
    member_id: UUID,
    data: FaceCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Store face record metadata & embedding for a home member."""
    record = backend_store.create_face_record(member_id=member_id, requesting_user_id=user_id, data=data)

    # Sync with local FaceDatabase for local AI pipeline recognition if member name available
    try:
        member = backend_store.get_member_by_id(member_id, user_id)
        if member and data.embedding:
            _, _, face_db = get_face_services()
            emb_np = np.array(data.embedding, dtype=np.float32)
            face_db.save_person(name=member["name"], embeddings=[emb_np])
    except Exception as e:
        print(f"Warning: Failed to sync face embedding to local FaceDatabase: {e}")

    return record


@router.post("/members/{member_id}/register-face", response_model=FaceResponse, status_code=status.HTTP_201_CREATED)
def register_member_face(
    member_id: UUID,
    data: FaceRegisterRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Enroll a new face for a home member using YuNet face detection & SFace 128D embeddings."""
    member = backend_store.get_member_by_id(member_id=member_id, requesting_user_id=user_id)
    detector, embedder, face_db = get_face_services()

    embedding_list: Optional[List[float]] = data.embedding
    image_path = data.image_path

    # Process base64 image if provided
    if data.image_base64:
        try:
            raw_bytes = base64.b64decode(data.image_base64)
            nparr = np.frombuffer(raw_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image payload.")

            faces = detector.detect_faces(frame)
            if not faces:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No face detected in image. Please ensure your face is clearly visible.",
                )
            if len(faces) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multiple faces detected in image. Please ensure only one face is visible.",
                )

            # Compute SFace 128D embedding
            emb_vector = embedder.compute_embedding(frame, faces[0])
            if emb_vector is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to extract SFace feature embedding from face image.",
                )

            embedding_list = emb_vector.tolist()
            if not image_path:
                image_path = f"data/faces/{member['name']}/enrollment_{member_id}.jpg"
                face_db.save_person(name=member["name"], embeddings=[emb_vector], face_images=[frame])

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image processing error: {str(e)}")

    if not embedding_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either valid image_base64 or explicit embedding vector must be provided.",
        )

    face_create = FaceCreate(
        image_path=image_path,
        embedding=embedding_list,
        sample_count=data.sample_count or len(embedding_list),
    )

    record = backend_store.create_face_record(member_id=member_id, requesting_user_id=user_id, data=face_create)
    return record


@router.get("/members/{member_id}/faces", response_model=List[FaceResponse])
def get_member_faces(
    member_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all face records belonging to a home member."""
    return backend_store.get_member_faces(member_id=member_id, requesting_user_id=user_id)


@router.get("/homes/{home_id}/face-records", response_model=List[Dict[str, Any]])
def get_home_face_records(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all face records (with embeddings & member names) belonging to a home."""
    return backend_store.get_home_face_records(home_id=home_id, requesting_user_id=user_id)


@router.delete("/faces/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_face_record(
    face_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a face record."""
    backend_store.delete_face_record(face_id=face_id, requesting_user_id=user_id)
    return None


@router.delete("/members/{member_id}/faces", status_code=status.HTTP_204_NO_CONTENT)
def clear_member_faces(
    member_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Clear all face records belonging to a home member."""
    backend_store.delete_member_faces(member_id=member_id, requesting_user_id=user_id)
    return None

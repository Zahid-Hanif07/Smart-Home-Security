from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_authenticated_device_session,
    get_current_user_id,
)
from app.models.face_occlusion_diagnostic import (
    FaceOcclusionDiagnosticCreate,
    FaceOcclusionDiagnosticResponse,
    FaceOcclusionStatusResponse,
)
from app.repositories.home_repository import home_repository
from app.services.face_occlusion_diagnostic_store import (
    OlderFaceOcclusionResultError,
    face_occlusion_diagnostic_store,
)


router = APIRouter(tags=["FaceOcc Diagnostics"])


@router.post(
    "",
    response_model=FaceOcclusionDiagnosticResponse,
    status_code=status.HTTP_201_CREATED,
)
def publish_face_occlusion(
    diagnostic: FaceOcclusionDiagnosticCreate,
    device_session: dict = Depends(get_authenticated_device_session),
):
    if diagnostic.home_id != device_session["home_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is not paired with the requested home.",
        )
    try:
        return face_occlusion_diagnostic_store.put(
            device_id=device_session["device_id"],
            diagnostic=diagnostic,
        )
    except OlderFaceOcclusionResultError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Diagnostic result is older than the current result.",
        ) from exc


@router.get(
    "/status",
    response_model=FaceOcclusionStatusResponse,
)
def get_face_occlusion_status(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    home_repository.get_home_by_id(home_id, user_id)
    return face_occlusion_diagnostic_store.get_home(home_id)

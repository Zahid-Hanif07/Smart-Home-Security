from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.dependencies import get_current_user_id
from app.models.security_log import SecurityLogCreate, SecurityLogResponse
from app.services.backend_store import backend_store

router = APIRouter()


@router.post("/homes/{home_id}/security-logs", response_model=SecurityLogResponse, status_code=status.HTTP_201_CREATED)
def create_security_log(
    home_id: UUID,
    data: SecurityLogCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new security log entry for a home."""
    return backend_store.create_security_log(home_id=home_id, requesting_user_id=user_id, data=data)


@router.get("/homes/{home_id}/security-logs", response_model=List[SecurityLogResponse])
def get_home_security_logs(
    home_id: UUID,
    event_type: Optional[str] = Query(None, description="Filter logs by event_type (e.g., motion_detected, authorized_person, unknown_person)"),
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve security event logs for a home with optional event_type filtering."""
    return backend_store.get_home_security_logs(home_id=home_id, requesting_user_id=user_id, event_type=event_type)

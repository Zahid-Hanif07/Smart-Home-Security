from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user_id
from app.models.alert import AlertCreate, AlertUpdate, AlertResponse
from app.services.backend_store import backend_store

router = APIRouter()


@router.post("/homes/{home_id}/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    home_id: UUID,
    data: AlertCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Trigger a new security alert for a home."""
    return backend_store.create_alert(home_id=home_id, requesting_user_id=user_id, data=data)


@router.get("/homes/{home_id}/alerts", response_model=List[AlertResponse])
def get_home_alerts(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Retrieve all security alerts for a home owned by the authenticated user."""
    return backend_store.get_home_alerts(home_id=home_id, requesting_user_id=user_id)


@router.put("/alerts/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(
    alert_id: UUID,
    update_data: AlertUpdate = AlertUpdate(is_read=True),
    user_id: UUID = Depends(get_current_user_id),
):
    """Mark an alert as read/unread."""
    return backend_store.mark_alert_read(
        alert_id=alert_id, requesting_user_id=user_id, is_read=update_data.is_read
    )


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a security alert."""
    backend_store.delete_alert(alert_id=alert_id, requesting_user_id=user_id)
    return None

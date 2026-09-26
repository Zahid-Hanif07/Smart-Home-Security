from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    security_log_id: Optional[UUID] = None
    alert_type: str
    title: str
    message: str
    image_path: Optional[str] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = True


class AlertResponse(AlertBase):
    id: UUID
    home_id: UUID
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

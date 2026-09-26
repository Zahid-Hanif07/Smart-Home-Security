from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SecurityLogBase(BaseModel):
    device_id: Optional[UUID] = None
    event_type: str
    description: Optional[str] = None
    person_name: Optional[str] = None
    is_authorized: Optional[bool] = None
    image_path: Optional[str] = None


class SecurityLogCreate(SecurityLogBase):
    pass


class SecurityLogResponse(SecurityLogBase):
    id: UUID
    home_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    device_name: str
    device_type: str
    device_identifier: Optional[str] = None
    status: Optional[str] = "offline"


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    status: Optional[str] = None
    last_seen: Optional[datetime] = None


class DeviceResponse(DeviceBase):
    id: UUID
    home_id: UUID
    created_at: datetime
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

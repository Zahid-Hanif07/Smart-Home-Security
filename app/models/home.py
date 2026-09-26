from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class HomeBase(BaseModel):
    name: str
    address: Optional[str] = None


class HomeCreate(HomeBase):
    pass


class HomeUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class HomeResponse(HomeBase):
    id: UUID
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

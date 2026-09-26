from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MemberBase(BaseModel):
    name: str
    relation: Optional[str] = None
    user_id: Optional[UUID] = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    user_id: Optional[UUID] = None


class MemberResponse(MemberBase):
    id: UUID
    home_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

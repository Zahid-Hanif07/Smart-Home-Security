from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


class ProfileBase(BaseModel):
    name: str
    email: EmailStr
    image_url: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None


class ProfileResponse(ProfileBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityLogBase(BaseModel):
    device_id: Optional[UUID] = None
    event_type: str = Field(min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=1000)
    person_name: Optional[str] = Field(default=None, max_length=120)
    is_authorized: Optional[bool] = None
    image_path: Optional[str] = Field(default=None, max_length=255)

    @field_validator("image_path")
    @classmethod
    def validate_evidence_key(cls, value):
        if value is not None and ("/" in value or "\\" in value or ":" in value or value in {".", ".."}):
            raise ValueError("image_path must be a storage key, not a filesystem path")
        return value


class SecurityLogCreate(SecurityLogBase):
    pass


class SecurityLogResponse(SecurityLogBase):
    id: UUID
    home_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertBase(BaseModel):
    security_log_id: Optional[UUID] = None
    alert_type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=1000)
    image_path: Optional[str] = Field(default=None, max_length=255)

    @field_validator("image_path")
    @classmethod
    def validate_evidence_key(cls, value):
        if value is not None and ("/" in value or "\\" in value or ":" in value or value in {".", ".."}):
            raise ValueError("image_path must be a storage key, not a filesystem path")
        return value


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

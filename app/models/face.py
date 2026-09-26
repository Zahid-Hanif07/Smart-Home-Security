from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FaceBase(BaseModel):
    image_path: Optional[str] = None
    embedding: Optional[List[Any]] = None
    sample_count: Optional[int] = 0


class FaceCreate(FaceBase):
    pass


class FaceResponse(FaceBase):
    id: UUID
    member_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

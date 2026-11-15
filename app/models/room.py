from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoomResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoomListResponse(BaseModel):
    rooms: list[RoomResponse]

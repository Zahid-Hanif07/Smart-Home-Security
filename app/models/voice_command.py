from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class VoiceCommandName(str, Enum):
    LIGHT_ON = "light_on"
    LIGHT_OFF = "light_off"
    ALL_LIGHTS_ON = "all_lights_on"
    ALL_LIGHTS_OFF = "all_lights_off"


class VoiceTargetType(str, Enum):
    ROOM = "room"
    ALL_LIGHTS = "all_lights"


class VoiceCommandCreate(BaseModel):
    client_command_id: UUID
    command: VoiceCommandName
    target_type: VoiceTargetType
    room_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_command_target(self):
        room_commands = {VoiceCommandName.LIGHT_ON, VoiceCommandName.LIGHT_OFF}
        all_lights_commands = {VoiceCommandName.ALL_LIGHTS_ON, VoiceCommandName.ALL_LIGHTS_OFF}
        if self.command in room_commands and self.target_type != VoiceTargetType.ROOM:
            raise ValueError("light_on and light_off require target_type=room")
        if self.command in all_lights_commands and self.target_type != VoiceTargetType.ALL_LIGHTS:
            raise ValueError("all_lights_on and all_lights_off require target_type=all_lights")
        if self.target_type == VoiceTargetType.ROOM and self.room_id is None:
            raise ValueError("room target requires room_id")
        if self.target_type == VoiceTargetType.ALL_LIGHTS and self.room_id is not None:
            raise ValueError("all_lights target must not include room_id")
        return self


class VoiceCommandResponse(BaseModel):
    id: UUID
    home_id: UUID
    owner_id: UUID
    client_command_id: UUID
    command: VoiceCommandName
    target_type: VoiceTargetType
    room_id: Optional[UUID] = None
    status: str
    expires_at: datetime
    terminal_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class VoiceCommandAccepted(BaseModel):
    command: VoiceCommandResponse
    existing: bool = False
    device_count: int = Field(default=0, ge=0)

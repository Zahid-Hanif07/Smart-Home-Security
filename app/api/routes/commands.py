from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user_id
from app.models.voice_command import VoiceCommandAccepted, VoiceCommandCreate, VoiceCommandResponse
from app.repositories.voice_command_repository import voice_command_repository

router = APIRouter()


@router.post("/homes/{home_id}/commands", response_model=VoiceCommandAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_command(home_id: UUID, data: VoiceCommandCreate, user_id: UUID = Depends(get_current_user_id)):
    return voice_command_repository.create(home_id, user_id, {
        "client_command_id": data.client_command_id,
        "command": data.command.value,
        "target_type": data.target_type.value,
        "room_id": data.room_id,
    })


@router.get("/homes/{home_id}/commands/{command_id}", response_model=VoiceCommandResponse)
def get_command(home_id: UUID, command_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    return voice_command_repository.get(home_id, user_id, command_id)

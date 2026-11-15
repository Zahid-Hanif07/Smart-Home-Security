import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException, status

from app.database.supabase_client import SupabaseClientManager
from app.repositories.home_repository import is_memory_fallback_enabled, is_supabase_configured
from app.repositories.home_repository import home_repository


class VoiceCommandRepository:
    def __init__(self):
        self._commands: Dict[UUID, Dict[str, Any]] = {}
        self._by_key: Dict[tuple[UUID, UUID], UUID] = {}
        self._in_memory_eligible_devices: Dict[UUID, list[UUID]] = {}

    def seed_in_memory_eligible_devices(self, home_id: UUID, device_ids: list[UUID]) -> None:
        """Test-only fixture hook; production eligibility comes from SQL capabilities."""
        self._in_memory_eligible_devices[home_id] = list(device_ids)

    def clear(self) -> None:
        self._commands.clear()
        self._by_key.clear()
        self._in_memory_eligible_devices.clear()

    @staticmethod
    def request_hash(data: Dict[str, Any]) -> str:
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create(self, home_id: UUID, owner_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        semantic = {
            "command": data["command"],
            "target_type": data["target_type"],
            "room_id": str(data["room_id"]) if data.get("room_id") else None,
        }
        request_hash = self.request_hash(semantic)
        client_id = data["client_command_id"]

        if not is_supabase_configured():
            if not is_memory_fallback_enabled():
                raise HTTPException(status_code=503, detail="Command service unavailable.")
            key = (home_id, client_id)
            home_repository.get_home_by_id(home_id, owner_id)
            existing_id = self._by_key.get(key)
            if existing_id:
                existing = self._commands[existing_id]
                if existing["request_hash"] != request_hash:
                    raise HTTPException(status_code=409, detail="Command idempotency conflict.")
                return {"command": existing, "existing": True, "device_count": existing["device_count"]}
            device_count = len(self._in_memory_eligible_devices.get(home_id, []))
            if device_count == 0:
                raise HTTPException(status_code=409, detail="No eligible light devices are available.")
            command_id = UUID(int=len(self._commands) + 1)
            now = datetime.now(timezone.utc)
            record = {
                "id": command_id, "home_id": home_id, "owner_id": owner_id,
                "client_command_id": client_id, "command": data["command"],
                "target_type": data["target_type"], "room_id": data.get("room_id"),
                "request_hash": request_hash, "status": "accepted",
                "expires_at": now + timedelta(minutes=5), "terminal_at": None,
                "resolved_at": None, "created_at": now, "device_count": device_count,
            }
            self._commands[command_id] = record
            self._by_key[key] = command_id
            return {"command": record, "existing": False, "device_count": device_count}

        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(status_code=503, detail="Command service unavailable.")
        try:
            response = client.rpc("create_voice_command", {
                "p_home_id": str(home_id),
                "p_owner_id": str(owner_id),
                "p_client_command_id": str(client_id),
                "p_command": data["command"],
                "p_target_type": data["target_type"],
                "p_room_id": str(data["room_id"]) if data.get("room_id") else None,
                "p_request_hash": request_hash,
                "p_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            }).execute()
            return response.data
        except Exception as exc:
            message = str(exc)
            if "idempotency_conflict" in message:
                raise HTTPException(status_code=409, detail="Command idempotency conflict.")
            if "no_eligible_devices" in message:
                raise HTTPException(status_code=409, detail="No eligible light devices are available.")
            if "invalid_room" in message or "invalid_target" in message:
                raise HTTPException(status_code=422, detail="Invalid command target.")
            if "home_not_authorized" in message:
                raise HTTPException(status_code=403, detail="Home access is not authorized.")
            raise HTTPException(status_code=503, detail="Command service unavailable.")

    def get(self, home_id: UUID, owner_id: UUID, command_id: UUID) -> Dict[str, Any]:
        if not is_supabase_configured():
            record = self._commands.get(command_id)
            if not record or record["home_id"] != home_id or record["owner_id"] != owner_id:
                raise HTTPException(status_code=404, detail="Command not found.")
            return record
        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(status_code=503, detail="Command service unavailable.")
        response = client.table("voice_commands").select("*").eq("id", str(command_id)).eq("home_id", str(home_id)).eq("owner_id", str(owner_id)).maybe_single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Command not found.")
        return response.data


voice_command_repository = VoiceCommandRepository()

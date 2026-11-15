from typing import Any, Dict, List
from uuid import UUID

from fastapi import HTTPException, status

from app.database.supabase_client import SupabaseClientManager
from app.repositories.home_repository import home_repository, is_memory_fallback_enabled, is_supabase_configured


class RoomRepository:
    def __init__(self) -> None:
        self._in_memory_rooms: Dict[UUID, Dict[str, Any]] = {}

    def seed_in_memory_room(self, room_id: UUID, home_id: UUID, name: str) -> None:
        self._in_memory_rooms[room_id] = {"id": room_id, "home_id": home_id, "name": name}

    def clear(self) -> None:
        self._in_memory_rooms.clear()

    def list_for_owner(self, home_id: UUID, owner_id: UUID) -> List[Dict[str, Any]]:
        home_repository.get_home_by_id(home_id, owner_id)
        if not is_supabase_configured():
            if not is_memory_fallback_enabled():
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Room service unavailable.")
            rooms = [room for room in self._in_memory_rooms.values() if room["home_id"] == home_id]
        else:
            client = SupabaseClientManager.get_admin_client()
            if not client:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Room service unavailable.")
            try:
                response = client.table("rooms").select("id,name").eq("home_id", str(home_id)).order("normalized_name").order("id").execute()
                rooms = response.data or []
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Room service unavailable.") from exc
        return sorted(
            ({"id": room["id"] if isinstance(room["id"], UUID) else UUID(str(room["id"])), "name": room["name"]} for room in rooms),
            key=lambda room: (room["name"].casefold(), str(room["id"])),
        )


room_repository = RoomRepository()

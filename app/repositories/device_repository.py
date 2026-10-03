import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.models.device import DeviceCreate, DeviceUpdate
from app.repositories.home_repository import home_repository, is_supabase_configured


class DeviceRepository:
    """Repository handling Device persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_devices: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        client = SupabaseClientManager.get_admin_client() or SupabaseClientManager.get_client()
        if not client or not is_supabase_configured():
            return None
        return client

    def create_device(self, home_id: UUID, requesting_user_id: UUID, data: DeviceCreate) -> Dict[str, Any]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                device_data = {
                    "home_id": str(home_id),
                    "device_name": data.device_name,
                    "device_type": data.device_type,
                    "device_identifier": data.device_identifier,
                    "status": data.status or "offline",
                }
                res = client.table("devices").insert(device_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["home_id"] = UUID(record["home_id"]) if isinstance(record["home_id"], str) else record["home_id"]
                    return record
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating device: {str(e)}",
                )

        device_id = uuid4()
        device = {
            "id": device_id,
            "home_id": home_id,
            "device_name": data.device_name,
            "device_type": data.device_type,
            "device_identifier": data.device_identifier,
            "status": data.status or "offline",
            "created_at": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc) if data.status == "online" else None,
        }
        self._in_memory_devices[device_id] = device
        return device

    def get_home_devices(self, home_id: UUID, requesting_user_id: UUID) -> List[Dict[str, Any]]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                res = client.table("devices").select("*").eq("home_id", str(home_id)).execute()
                devices = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["home_id"] = UUID(item["home_id"]) if isinstance(item["home_id"], str) else item["home_id"]
                    devices.append(item)
                return devices
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing devices: {str(e)}",
                )

        return [d for d in self._in_memory_devices.values() if d["home_id"] == home_id]

    def update_device(self, device_id: UUID, requesting_user_id: UUID, data: DeviceUpdate) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                res_dev = client.table("devices").select("home_id").eq("id", str(device_id)).execute()
                if not res_dev.data or len(res_dev.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
                home_id = UUID(res_dev.data[0]["home_id"])
                home_repository.get_home_by_id(home_id, requesting_user_id)

                update_data = {}
                if data.device_name is not None:
                    update_data["device_name"] = data.device_name
                if data.device_type is not None:
                    update_data["device_type"] = data.device_type
                if data.status is not None:
                    update_data["status"] = data.status
                if data.last_seen is not None:
                    update_data["last_seen"] = data.last_seen.isoformat()

                res = client.table("devices").update(update_data).eq("id", str(device_id)).execute()
                if res.data and len(res.data) > 0:
                    updated = res.data[0]
                    updated["id"] = UUID(updated["id"]) if isinstance(updated["id"], str) else updated["id"]
                    updated["home_id"] = UUID(updated["home_id"]) if isinstance(updated["home_id"], str) else updated["home_id"]
                    return updated
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error updating device: {str(e)}",
                )

        device = self._in_memory_devices.get(device_id)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

        home_repository.get_home_by_id(device["home_id"], requesting_user_id)
        if data.device_name is not None:
            device["device_name"] = data.device_name
        if data.device_type is not None:
            device["device_type"] = data.device_type
        if data.status is not None:
            device["status"] = data.status
        if data.last_seen is not None:
            device["last_seen"] = data.last_seen
        return device

    def delete_device(self, device_id: UUID, requesting_user_id: UUID) -> bool:
        client = self._get_client()
        if client:
            try:
                res_dev = client.table("devices").select("home_id").eq("id", str(device_id)).execute()
                if not res_dev.data or len(res_dev.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
                home_id = UUID(res_dev.data[0]["home_id"])
                home_repository.get_home_by_id(home_id, requesting_user_id)

                client.table("devices").delete().eq("id", str(device_id)).execute()
                return True
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error deleting device: {str(e)}",
                )

        device = self._in_memory_devices.get(device_id)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
        home_repository.get_home_by_id(device["home_id"], requesting_user_id)
        del self._in_memory_devices[device_id]
        return True


device_repository = DeviceRepository()

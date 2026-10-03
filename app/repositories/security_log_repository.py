import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.models.security_log import SecurityLogCreate
from app.repositories.home_repository import home_repository, is_supabase_configured


class SecurityLogRepository:
    """Repository handling Security Log persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_logs: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        client = SupabaseClientManager.get_admin_client() or SupabaseClientManager.get_client()
        if not client or not is_supabase_configured():
            return None
        return client

    def create_security_log(self, home_id: UUID, requesting_user_id: UUID, data: SecurityLogCreate) -> Dict[str, Any]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                log_data = {
                    "home_id": str(home_id),
                    "device_id": str(data.device_id) if data.device_id else None,
                    "event_type": data.event_type,
                    "description": data.description,
                    "person_name": data.person_name,
                    "is_authorized": data.is_authorized,
                    "image_path": data.image_path,
                }
                res = client.table("security_logs").insert(log_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["home_id"] = UUID(record["home_id"]) if isinstance(record["home_id"], str) else record["home_id"]
                    if record.get("device_id"):
                        record["device_id"] = UUID(record["device_id"]) if isinstance(record["device_id"], str) else record["device_id"]
                    return record
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating security log: {str(e)}",
                )

        log_id = uuid4()
        log_entry = {
            "id": log_id,
            "home_id": home_id,
            "device_id": data.device_id,
            "event_type": data.event_type,
            "description": data.description,
            "person_name": data.person_name,
            "is_authorized": data.is_authorized,
            "image_path": data.image_path,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_logs[log_id] = log_entry
        return log_entry

    def get_home_security_logs(
        self, home_id: UUID, requesting_user_id: UUID, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                query = client.table("security_logs").select("*").eq("home_id", str(home_id))
                if event_type:
                    query = query.eq("event_type", event_type)
                res = query.order("created_at", desc=True).execute()
                logs = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["home_id"] = UUID(item["home_id"]) if isinstance(item["home_id"], str) else item["home_id"]
                    if item.get("device_id"):
                        item["device_id"] = UUID(item["device_id"]) if isinstance(item["device_id"], str) else item["device_id"]
                    logs.append(item)
                return logs
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing security logs: {str(e)}",
                )

        logs = [l for l in self._in_memory_logs.values() if l["home_id"] == home_id]
        if event_type:
            logs = [l for l in logs if l["event_type"].lower() == event_type.lower()]
        return sorted(logs, key=lambda x: x["created_at"], reverse=True)


security_log_repository = SecurityLogRepository()

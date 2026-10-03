import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.models.alert import AlertCreate, AlertUpdate
from app.repositories.home_repository import home_repository, is_supabase_configured


class AlertRepository:
    """Repository handling Alert persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_alerts: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        client = SupabaseClientManager.get_admin_client() or SupabaseClientManager.get_client()
        if not client or not is_supabase_configured():
            return None
        return client

    def create_alert(self, home_id: UUID, requesting_user_id: UUID, data: AlertCreate) -> Dict[str, Any]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                alert_data = {
                    "home_id": str(home_id),
                    "security_log_id": str(data.security_log_id) if data.security_log_id else None,
                    "alert_type": data.alert_type,
                    "title": data.title,
                    "message": data.message,
                    "image_path": data.image_path,
                    "is_read": False,
                }
                res = client.table("alerts").insert(alert_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["home_id"] = UUID(record["home_id"]) if isinstance(record["home_id"], str) else record["home_id"]
                    if record.get("security_log_id"):
                        record["security_log_id"] = UUID(record["security_log_id"]) if isinstance(record["security_log_id"], str) else record["security_log_id"]
                    return record
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating alert: {str(e)}",
                )

        alert_id = uuid4()
        alert = {
            "id": alert_id,
            "home_id": home_id,
            "security_log_id": data.security_log_id,
            "alert_type": data.alert_type,
            "title": data.title,
            "message": data.message,
            "image_path": data.image_path,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_alerts[alert_id] = alert
        return alert

    def get_home_alerts(self, home_id: UUID, requesting_user_id: UUID) -> List[Dict[str, Any]]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                res = client.table("alerts").select("*").eq("home_id", str(home_id)).order("created_at", desc=True).execute()
                alerts = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["home_id"] = UUID(item["home_id"]) if isinstance(item["home_id"], str) else item["home_id"]
                    if item.get("security_log_id"):
                        item["security_log_id"] = UUID(item["security_log_id"]) if isinstance(item["security_log_id"], str) else item["security_log_id"]
                    alerts.append(item)
                return alerts
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing alerts: {str(e)}",
                )

        alerts = [a for a in self._in_memory_alerts.values() if a["home_id"] == home_id]
        return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

    def mark_alert_read(self, alert_id: UUID, requesting_user_id: UUID, is_read: bool = True) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                res_alert = client.table("alerts").select("home_id").eq("id", str(alert_id)).execute()
                if not res_alert.data or len(res_alert.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
                home_id = UUID(res_alert.data[0]["home_id"])
                home_repository.get_home_by_id(home_id, requesting_user_id)

                res = client.table("alerts").update({"is_read": is_read}).eq("id", str(alert_id)).execute()
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
                    detail=f"Database error updating alert: {str(e)}",
                )

        alert = self._in_memory_alerts.get(alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
        home_repository.get_home_by_id(alert["home_id"], requesting_user_id)
        alert["is_read"] = is_read
        return alert

    def delete_alert(self, alert_id: UUID, requesting_user_id: UUID) -> bool:
        client = self._get_client()
        if client:
            try:
                res_alert = client.table("alerts").select("home_id").eq("id", str(alert_id)).execute()
                if not res_alert.data or len(res_alert.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
                home_id = UUID(res_alert.data[0]["home_id"])
                home_repository.get_home_by_id(home_id, requesting_user_id)

                client.table("alerts").delete().eq("id", str(alert_id)).execute()
                return True
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error deleting alert: {str(e)}",
                )

        alert = self._in_memory_alerts.get(alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
        home_repository.get_home_by_id(alert["home_id"], requesting_user_id)
        del self._in_memory_alerts[alert_id]
        return True


alert_repository = AlertRepository()

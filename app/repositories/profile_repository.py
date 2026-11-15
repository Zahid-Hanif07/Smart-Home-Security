import os
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.config.backend_settings import settings
from app.models.user import ProfileUpdate
from app.repositories.home_repository import is_supabase_configured, is_memory_fallback_enabled


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class ProfileRepository:
    """Repository handling User Profile persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_profiles: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        if not is_supabase_configured():
            if is_memory_fallback_enabled():
                return None
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured; persistent profile writes are unavailable.")
        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service-role database access is unavailable; persistent writes are disabled.",
            )
        return client

    def get_profile(self, user_id: Any) -> Optional[Dict[str, Any]]:
        u_uuid = _to_uuid(user_id)
        client = self._get_client()
        if client:
            try:
                res = client.table("profiles").select("*").eq("id", str(u_uuid)).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    return record
                return None
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error fetching profile: {str(e)}",
                )

        return self._in_memory_profiles.get(u_uuid)

    def get_or_create_profile(self, user_id: Any, email: str, name: str) -> Dict[str, Any]:
        u_uuid = _to_uuid(user_id)
        client = self._get_client()
        if client:
            try:
                # 1. Check if profile already exists in Supabase
                res = client.table("profiles").select("*").eq("id", str(u_uuid)).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    return record

                # 2. Insert new profile record if not present
                profile_data = {
                    "id": str(u_uuid),
                    "name": name,
                    "email": email,
                    "image_url": None,
                }
                admin_client = SupabaseClientManager.get_admin_client() or client
                insert_res = admin_client.table("profiles").insert(profile_data).execute()
                if insert_res.data and len(insert_res.data) > 0:
                    record = insert_res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    return record
                raise RuntimeError("Supabase returned no row after profile insert")
            except Exception as e:
                # If trigger inserted concurrently, attempt fetch
                try:
                    res_retry = client.table("profiles").select("*").eq("id", str(u_uuid)).execute()
                    if res_retry.data and len(res_retry.data) > 0:
                        record = res_retry.data[0]
                        record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                        return record
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error ensuring profile: {str(e)}",
                )

        if u_uuid not in self._in_memory_profiles:
            self._in_memory_profiles[u_uuid] = {
                "id": u_uuid,
                "name": name,
                "email": email,
                "image_url": None,
                "created_at": datetime.now(timezone.utc),
            }
        return self._in_memory_profiles[u_uuid]

    def update_profile(self, user_id: Any, update_data: ProfileUpdate) -> Dict[str, Any]:
        u_uuid = _to_uuid(user_id)
        client = self._get_client()
        if client:
            try:
                fields_to_update = {}
                if update_data.name is not None:
                    fields_to_update["name"] = update_data.name
                if update_data.image_url is not None:
                    fields_to_update["image_url"] = update_data.image_url

                if not fields_to_update:
                    profile = self.get_profile(u_uuid)
                    if not profile:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
                    return profile

                admin_client = SupabaseClientManager.get_admin_client() or client
                res = admin_client.table("profiles").update(fields_to_update).eq("id", str(u_uuid)).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    return record
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile update was not applied.")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error updating profile: {str(e)}",
                )

        profile = self._in_memory_profiles.get(u_uuid)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        if update_data.name is not None:
            profile["name"] = update_data.name
        if update_data.image_url is not None:
            profile["image_url"] = update_data.image_url

        return profile

    def clear(self) -> None:
        self._in_memory_profiles.clear()


profile_repository = ProfileRepository()

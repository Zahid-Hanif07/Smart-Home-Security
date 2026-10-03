import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.config.backend_settings import settings
from app.models.member import MemberCreate, MemberUpdate, MemberResponse
from app.repositories.home_repository import home_repository, is_supabase_configured


class MemberRepository:
    """Repository handling Home Member persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_members: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        client = SupabaseClientManager.get_admin_client() or SupabaseClientManager.get_client()
        if not client or not is_supabase_configured():
            return None
        return client

    def create_member(self, home_id: UUID, requesting_user_id: UUID, data: MemberCreate) -> Dict[str, Any]:
        # Verify ownership of target home
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                member_data = {
                    "home_id": str(home_id),
                    "user_id": str(data.user_id) if data.user_id else None,
                    "name": data.name,
                    "relation": data.relation,
                }
                res = client.table("home_members").insert(member_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["home_id"] = UUID(record["home_id"]) if isinstance(record["home_id"], str) else record["home_id"]
                    if record.get("user_id"):
                        record["user_id"] = UUID(record["user_id"]) if isinstance(record["user_id"], str) else record["user_id"]
                    return record
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating member: {str(e)}",
                )

        member_id = uuid4()
        member = {
            "id": member_id,
            "home_id": home_id,
            "user_id": data.user_id,
            "name": data.name,
            "relation": data.relation,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_members[member_id] = member
        return member

    def get_home_members(self, home_id: UUID, requesting_user_id: UUID) -> List[Dict[str, Any]]:
        home_repository.get_home_by_id(home_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                res = client.table("home_members").select("*").eq("home_id", str(home_id)).execute()
                members = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["home_id"] = UUID(item["home_id"]) if isinstance(item["home_id"], str) else item["home_id"]
                    if item.get("user_id"):
                        item["user_id"] = UUID(item["user_id"]) if isinstance(item["user_id"], str) else item["user_id"]
                    members.append(item)
                return members
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing home members: {str(e)}",
                )

        return [m for m in self._in_memory_members.values() if m["home_id"] == home_id]

    def get_member_by_id(self, member_id: UUID, requesting_user_id: UUID) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                res = client.table("home_members").select("*").eq("id", str(member_id)).execute()
                if not res.data or len(res.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
                member = res.data[0]
                home_id = UUID(member["home_id"]) if isinstance(member["home_id"], str) else member["home_id"]
                # Verify home ownership
                home_repository.get_home_by_id(home_id, requesting_user_id)

                member["id"] = UUID(member["id"]) if isinstance(member["id"], str) else member["id"]
                member["home_id"] = home_id
                if member.get("user_id"):
                    member["user_id"] = UUID(member["user_id"]) if isinstance(member["user_id"], str) else member["user_id"]
                return member
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error fetching member: {str(e)}",
                )

        member = self._in_memory_members.get(member_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
        home_repository.get_home_by_id(member["home_id"], requesting_user_id)
        return member

    def update_member(self, member_id: UUID, requesting_user_id: UUID, data: MemberUpdate) -> Dict[str, Any]:
        member = self.get_member_by_id(member_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                update_data = {}
                if data.name is not None:
                    update_data["name"] = data.name
                if data.relation is not None:
                    update_data["relation"] = data.relation
                if data.user_id is not None:
                    update_data["user_id"] = str(data.user_id)
                if not update_data:
                    return member

                res = client.table("home_members").update(update_data).eq("id", str(member_id)).execute()
                if res.data and len(res.data) > 0:
                    updated = res.data[0]
                    updated["id"] = UUID(updated["id"]) if isinstance(updated["id"], str) else updated["id"]
                    updated["home_id"] = UUID(updated["home_id"]) if isinstance(updated["home_id"], str) else updated["home_id"]
                    if updated.get("user_id"):
                        updated["user_id"] = UUID(updated["user_id"]) if isinstance(updated["user_id"], str) else updated["user_id"]
                    return updated
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error updating member: {str(e)}",
                )

        if data.name is not None:
            member["name"] = data.name
        if data.relation is not None:
            member["relation"] = data.relation
        if data.user_id is not None:
            member["user_id"] = data.user_id
        return member

    def delete_member(self, member_id: UUID, requesting_user_id: UUID) -> bool:
        member = self.get_member_by_id(member_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                client.table("home_members").delete().eq("id", str(member_id)).execute()
                return True
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error deleting member: {str(e)}",
                )

        if member_id in self._in_memory_members:
            del self._in_memory_members[member_id]
        return True


member_repository = MemberRepository()

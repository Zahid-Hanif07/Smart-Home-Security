import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.config.backend_settings import settings
from app.models.face import FaceCreate, FaceResponse
from app.repositories.home_repository import is_supabase_configured
from app.repositories.member_repository import member_repository


class FaceRepository:
    """Repository handling Face Record persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_faces: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        client = SupabaseClientManager.get_admin_client() or SupabaseClientManager.get_client()
        if not client or not is_supabase_configured():
            return None
        return client

    def create_face_record(self, member_id: UUID, requesting_user_id: UUID, data: FaceCreate) -> Dict[str, Any]:
        # Verify ownership of member and home
        member = member_repository.get_member_by_id(member_id, requesting_user_id)

        sample_count = data.sample_count
        if sample_count is None or sample_count == 0:
            sample_count = len(data.embedding) if data.embedding else 1

        client = self._get_client()
        if client:
            try:
                face_data = {
                    "member_id": str(member_id),
                    "image_path": data.image_path,
                    "embedding": data.embedding,
                    "sample_count": sample_count,
                }
                res = client.table("face_records").insert(face_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["member_id"] = UUID(record["member_id"]) if isinstance(record["member_id"], str) else record["member_id"]
                    return record
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating face record: {str(e)}",
                )

        face_id = uuid4()
        face_record = {
            "id": face_id,
            "member_id": member_id,
            "image_path": data.image_path,
            "embedding": data.embedding,
            "sample_count": sample_count,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_faces[face_id] = face_record
        return face_record

    def get_member_faces(self, member_id: UUID, requesting_user_id: UUID) -> List[Dict[str, Any]]:
        member_repository.get_member_by_id(member_id, requesting_user_id)

        client = self._get_client()
        if client:
            try:
                res = client.table("face_records").select("*").eq("member_id", str(member_id)).execute()
                faces = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["member_id"] = UUID(item["member_id"]) if isinstance(item["member_id"], str) else item["member_id"]
                    faces.append(item)
                return faces
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing member face records: {str(e)}",
                )

        return [f for f in self._in_memory_faces.values() if f["member_id"] == member_id]

    def get_home_face_records(self, home_id: UUID, requesting_user_id: UUID) -> List[Dict[str, Any]]:
        # Verify ownership of home
        members = member_repository.get_home_members(home_id, requesting_user_id)
        member_map = {m["id"]: m["name"] for m in members}

        if not member_map:
            return []

        client = self._get_client()
        if client:
            try:
                res = client.table("face_records").select("*, home_members!inner(name, home_id)").eq("home_members.home_id", str(home_id)).execute()
                records = []
                for item in res.data or []:
                    hm_data = item.pop("home_members", {})
                    item["member_name"] = hm_data.get("name", "Member") if isinstance(hm_data, dict) else "Member"
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["member_id"] = UUID(item["member_id"]) if isinstance(item["member_id"], str) else item["member_id"]
                    records.append(item)
                return records
            except Exception:
                # Fallback: Query face_records per member
                records = []
                for m_id, m_name in member_map.items():
                    res = client.table("face_records").select("*").eq("member_id", str(m_id)).execute()
                    for item in res.data or []:
                        item["member_name"] = m_name
                        item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                        item["member_id"] = UUID(item["member_id"]) if isinstance(item["member_id"], str) else item["member_id"]
                        records.append(item)
                return records

        records = []
        for f in self._in_memory_faces.values():
            if f["member_id"] in member_map:
                f_copy = dict(f)
                f_copy["member_name"] = member_map[f["member_id"]]
                records.append(f_copy)
        return records

    def delete_face_record(self, face_id: UUID, requesting_user_id: UUID) -> bool:
        client = self._get_client()
        if client:
            try:
                res = client.table("face_records").select("member_id").eq("id", str(face_id)).execute()
                if not res.data or len(res.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face record not found.")
                member_id = UUID(res.data[0]["member_id"])
                member_repository.get_member_by_id(member_id, requesting_user_id)

                client.table("face_records").delete().eq("id", str(face_id)).execute()
                return True
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error deleting face record: {str(e)}",
                )

        face = self._in_memory_faces.get(face_id)
        if not face:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face record not found.")

        member_repository.get_member_by_id(face["member_id"], requesting_user_id)
        del self._in_memory_faces[face_id]
        return True

    def delete_member_faces(self, member_id: UUID, requesting_user_id: UUID) -> bool:
        member_repository.get_member_by_id(member_id, requesting_user_id)
        client = self._get_client()
        if client:
            try:
                client.table("face_records").delete().eq("member_id", str(member_id)).execute()
                return True
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error clearing member face records: {str(e)}",
                )

        to_remove = [fid for fid, f in self._in_memory_faces.items() if f["member_id"] == member_id]
        for fid in to_remove:
            del self._in_memory_faces[fid]
        return True


face_repository = FaceRepository()

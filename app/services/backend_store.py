from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models import (
    ProfileResponse,
    ProfileUpdate,
    HomeCreate,
    HomeUpdate,
    HomeResponse,
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    FaceCreate,
    FaceResponse,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    SecurityLogCreate,
    SecurityLogResponse,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
)


def _to_uuid(val: Any) -> UUID:
    """Helper to convert string or UUID to UUID object."""
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class BackendStore:
    """In-memory & Supabase database repository providing strict relational isolation and RLS authorization."""

    def __init__(self):
        self.profiles: Dict[UUID, Dict[str, Any]] = {}
        self.homes: Dict[UUID, Dict[str, Any]] = {}
        self.home_members: Dict[UUID, Dict[str, Any]] = {}
        self.face_records: Dict[UUID, Dict[str, Any]] = {}
        self.devices: Dict[UUID, Dict[str, Any]] = {}
        self.security_logs: Dict[UUID, Dict[str, Any]] = {}
        self.alerts: Dict[UUID, Dict[str, Any]] = {}

    def clear(self) -> None:
        """Reset state for clean automated test execution."""
        self.profiles.clear()
        self.homes.clear()
        self.home_members.clear()
        self.face_records.clear()
        self.devices.clear()
        self.security_logs.clear()
        self.alerts.clear()

    # -------------------------------------------------------------------------
    # PROFILES
    # -------------------------------------------------------------------------
    def get_or_create_profile(self, user_id: Any, email: str, name: str) -> Dict[str, Any]:
        u_uuid = _to_uuid(user_id)
        if u_uuid not in self.profiles:
            self.profiles[u_uuid] = {
                "id": u_uuid,
                "name": name,
                "email": email,
                "image_url": None,
                "created_at": datetime.now(timezone.utc),
            }
        return self.profiles[u_uuid]

    def update_profile(self, user_id: Any, update_data: ProfileUpdate) -> Dict[str, Any]:
        u_uuid = _to_uuid(user_id)
        profile = self.profiles.get(u_uuid)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        if update_data.name is not None:
            profile["name"] = update_data.name
        if update_data.image_url is not None:
            profile["image_url"] = update_data.image_url

        return profile

    # -------------------------------------------------------------------------
    # HOMES
    # -------------------------------------------------------------------------
    def create_home(self, owner_id: Any, data: HomeCreate) -> Dict[str, Any]:
        o_uuid = _to_uuid(owner_id)
        home_id = uuid4()
        home = {
            "id": home_id,
            "owner_id": o_uuid,
            "name": data.name,
            "address": data.address,
            "created_at": datetime.now(timezone.utc),
        }
        self.homes[home_id] = home
        return home

    def get_user_homes(self, owner_id: Any) -> List[Dict[str, Any]]:
        o_uuid = _to_uuid(owner_id)
        return [h for h in self.homes.values() if h["owner_id"] == o_uuid]

    def get_home_by_id(self, home_id: Any, requesting_user_id: Any) -> Dict[str, Any]:
        h_uuid = _to_uuid(home_id)
        u_uuid = _to_uuid(requesting_user_id)

        home = self.homes.get(h_uuid)
        if not home:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home not found.")
        if home["owner_id"] != u_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this home.",
            )
        return home

    def update_home(self, home_id: Any, requesting_user_id: Any, data: HomeUpdate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        if data.name is not None:
            home["name"] = data.name
        if data.address is not None:
            home["address"] = data.address
        return home

    def delete_home(self, home_id: Any, requesting_user_id: Any) -> bool:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]
        del self.homes[h_uuid]

        # Cascade delete members, devices, logs, alerts
        member_ids = [m_id for m_id, m in self.home_members.items() if m["home_id"] == h_uuid]
        for m_id in member_ids:
            del self.home_members[m_id]

        device_ids = [d_id for d_id, d in self.devices.items() if d["home_id"] == h_uuid]
        for d_id in device_ids:
            del self.devices[d_id]

        log_ids = [l_id for l_id, l in self.security_logs.items() if l["home_id"] == h_uuid]
        for l_id in log_ids:
            del self.security_logs[l_id]

        alert_ids = [a_id for a_id, a in self.alerts.items() if a["home_id"] == h_uuid]
        for a_id in alert_ids:
            del self.alerts[a_id]

        return True

    # -------------------------------------------------------------------------
    # HOME MEMBERS
    # -------------------------------------------------------------------------
    def create_member(self, home_id: Any, requesting_user_id: Any, data: MemberCreate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]

        member_id = uuid4()
        member = {
            "id": member_id,
            "home_id": h_uuid,
            "user_id": _to_uuid(data.user_id) if data.user_id else None,
            "name": data.name,
            "relation": data.relation,
            "created_at": datetime.now(timezone.utc),
        }
        self.home_members[member_id] = member
        return member

    def get_home_members(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]
        return [m for m in self.home_members.values() if m["home_id"] == h_uuid]

    def update_member(self, member_id: Any, requesting_user_id: Any, data: MemberUpdate) -> Dict[str, Any]:
        m_uuid = _to_uuid(member_id)
        member = self.home_members.get(m_uuid)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        # Verify home ownership
        self.get_home_by_id(member["home_id"], requesting_user_id)

        if data.name is not None:
            member["name"] = data.name
        if data.relation is not None:
            member["relation"] = data.relation
        if data.user_id is not None:
            member["user_id"] = _to_uuid(data.user_id)

        return member

    def delete_member(self, member_id: Any, requesting_user_id: Any) -> bool:
        m_uuid = _to_uuid(member_id)
        member = self.home_members.get(m_uuid)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        self.get_home_by_id(member["home_id"], requesting_user_id)
        del self.home_members[m_uuid]

        # Cascade delete face records
        face_ids = [f_id for f_id, f in self.face_records.items() if f["member_id"] == m_uuid]
        for f_id in face_ids:
            del self.face_records[f_id]

        return True

    # -------------------------------------------------------------------------
    # FACE RECORDS
    # -------------------------------------------------------------------------
    def create_face_record(self, member_id: Any, requesting_user_id: Any, data: FaceCreate) -> Dict[str, Any]:
        m_uuid = _to_uuid(member_id)
        member = self.home_members.get(m_uuid)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        self.get_home_by_id(member["home_id"], requesting_user_id)

        face_id = uuid4()
        face_record = {
            "id": face_id,
            "member_id": m_uuid,
            "image_path": data.image_path,
            "embedding": data.embedding,
            "sample_count": data.sample_count or (len(data.embedding) if data.embedding else 0),
            "created_at": datetime.now(timezone.utc),
        }
        self.face_records[face_id] = face_record
        return face_record

    def get_member_faces(self, member_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        m_uuid = _to_uuid(member_id)
        member = self.home_members.get(m_uuid)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

        self.get_home_by_id(member["home_id"], requesting_user_id)
        return [f for f in self.face_records.values() if f["member_id"] == m_uuid]

    def delete_face_record(self, face_id: Any, requesting_user_id: Any) -> bool:
        f_uuid = _to_uuid(face_id)
        face = self.face_records.get(f_uuid)
        if not face:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face record not found.")

        member = self.home_members.get(face["member_id"])
        if member:
            self.get_home_by_id(member["home_id"], requesting_user_id)

        del self.face_records[f_uuid]
        return True

    # -------------------------------------------------------------------------
    # DEVICES
    # -------------------------------------------------------------------------
    def create_device(self, home_id: Any, requesting_user_id: Any, data: DeviceCreate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]

        device_id = uuid4()
        device = {
            "id": device_id,
            "home_id": h_uuid,
            "device_name": data.device_name,
            "device_type": data.device_type,
            "device_identifier": data.device_identifier,
            "status": data.status or "offline",
            "created_at": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc) if data.status == "online" else None,
        }
        self.devices[device_id] = device
        return device

    def get_home_devices(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]
        return [d for d in self.devices.values() if d["home_id"] == h_uuid]

    def update_device(self, device_id: Any, requesting_user_id: Any, data: DeviceUpdate) -> Dict[str, Any]:
        d_uuid = _to_uuid(device_id)
        device = self.devices.get(d_uuid)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

        self.get_home_by_id(device["home_id"], requesting_user_id)

        if data.device_name is not None:
            device["device_name"] = data.device_name
        if data.device_type is not None:
            device["device_type"] = data.device_type
        if data.status is not None:
            device["status"] = data.status
        if data.last_seen is not None:
            device["last_seen"] = data.last_seen

        return device

    def delete_device(self, device_id: Any, requesting_user_id: Any) -> bool:
        d_uuid = _to_uuid(device_id)
        device = self.devices.get(d_uuid)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

        self.get_home_by_id(device["home_id"], requesting_user_id)
        del self.devices[d_uuid]
        return True

    # -------------------------------------------------------------------------
    # SECURITY LOGS
    # -------------------------------------------------------------------------
    def create_security_log(self, home_id: Any, requesting_user_id: Any, data: SecurityLogCreate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]

        log_id = uuid4()
        log_entry = {
            "id": log_id,
            "home_id": h_uuid,
            "device_id": _to_uuid(data.device_id) if data.device_id else None,
            "event_type": data.event_type,
            "description": data.description,
            "person_name": data.person_name,
            "is_authorized": data.is_authorized,
            "image_path": data.image_path,
            "created_at": datetime.now(timezone.utc),
        }
        self.security_logs[log_id] = log_entry
        return log_entry

    def get_home_security_logs(
        self, home_id: Any, requesting_user_id: Any, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]
        logs = [l for l in self.security_logs.values() if l["home_id"] == h_uuid]
        if event_type:
            logs = [l for l in logs if l["event_type"].lower() == event_type.lower()]
        return sorted(logs, key=lambda x: x["created_at"], reverse=True)

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------
    def create_alert(self, home_id: Any, requesting_user_id: Any, data: AlertCreate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]

        alert_id = uuid4()
        alert = {
            "id": alert_id,
            "home_id": h_uuid,
            "security_log_id": _to_uuid(data.security_log_id) if data.security_log_id else None,
            "alert_type": data.alert_type,
            "title": data.title,
            "message": data.message,
            "image_path": data.image_path,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        }
        self.alerts[alert_id] = alert
        return alert

    def get_home_alerts(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        h_uuid = home["id"]
        alerts = [a for a in self.alerts.values() if a["home_id"] == h_uuid]
        return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

    def mark_alert_read(self, alert_id: Any, requesting_user_id: Any, is_read: bool = True) -> Dict[str, Any]:
        a_uuid = _to_uuid(alert_id)
        alert = self.alerts.get(a_uuid)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

        self.get_home_by_id(alert["home_id"], requesting_user_id)
        alert["is_read"] = is_read
        return alert

    def delete_alert(self, alert_id: Any, requesting_user_id: Any) -> bool:
        a_uuid = _to_uuid(alert_id)
        alert = self.alerts.get(a_uuid)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

        self.get_home_by_id(alert["home_id"], requesting_user_id)
        del self.alerts[a_uuid]
        return True


backend_store = BackendStore()

from typing import Dict, List, Optional, Any
from uuid import UUID
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
from app.repositories import (
    home_repository,
    member_repository,
    face_repository,
    security_log_repository,
    alert_repository,
    device_repository,
    profile_repository,
)


def _to_uuid(val: Any) -> UUID:
    """Helper to convert string or UUID to UUID object."""
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class BackendStore:
    """Repository façade delegating to structured Supabase PostgreSQL Repositories."""

    def __init__(self):
        pass

    @property
    def profiles(self) -> Dict[UUID, Dict[str, Any]]:
        return profile_repository._in_memory_profiles

    def clear(self) -> None:
        """Reset internal states for clean automated test execution.

        Clears every in-memory repository so each test class begins with a
        completely empty store.  Import of pairing_repository is deferred to
        this method to avoid a circular import at module load time
        (pairing_repository → home_repository → BackendStore would cycle).
        """
        # Standard repositories (mirrors their _in_memory_* dict directly)
        profile_repository.clear()
        home_repository._in_memory_homes.clear()
        member_repository._in_memory_members.clear()
        face_repository._in_memory_faces.clear()
        device_repository._in_memory_devices.clear()
        security_log_repository._in_memory_logs.clear()
        alert_repository._in_memory_alerts.clear()

        # Pairing repository — imported here to avoid circular imports at
        # module level (pairing_repository depends on home_repository).
        from app.repositories.pairing_repository import pairing_repository as _pairing_repo
        _pairing_repo.clear()
        from app.repositories.voice_command_repository import voice_command_repository
        voice_command_repository.clear()
        from app.repositories.room_repository import room_repository
        room_repository.clear()

    # -------------------------------------------------------------------------
    # PROFILES
    # -------------------------------------------------------------------------
    def get_or_create_profile(self, user_id: Any, email: str, name: str) -> Dict[str, Any]:
        return profile_repository.get_or_create_profile(user_id=user_id, email=email, name=name)

    def update_profile(self, user_id: Any, update_data: ProfileUpdate) -> Dict[str, Any]:
        return profile_repository.update_profile(user_id=user_id, update_data=update_data)

    # -------------------------------------------------------------------------
    # HOMES
    # -------------------------------------------------------------------------
    def create_home(self, owner_id: Any, data: HomeCreate) -> Dict[str, Any]:
        return home_repository.create_home(owner_id=_to_uuid(owner_id), data=data)

    def ensure_initial_home(self, owner_id: Any) -> Dict[str, Any]:
        return home_repository.ensure_initial_home(owner_id=_to_uuid(owner_id))

    def get_user_homes(self, owner_id: Any) -> List[Dict[str, Any]]:
        return home_repository.get_user_homes(owner_id=_to_uuid(owner_id))

    def get_home_by_id(self, home_id: Any, requesting_user_id: Any) -> Dict[str, Any]:
        return home_repository.get_home_by_id(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def update_home(self, home_id: Any, requesting_user_id: Any, data: HomeUpdate) -> Dict[str, Any]:
        return home_repository.update_home(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def delete_home(self, home_id: Any, requesting_user_id: Any) -> bool:
        return home_repository.delete_home(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def list_rooms(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        from app.repositories.room_repository import room_repository
        return room_repository.list_for_owner(_to_uuid(home_id), _to_uuid(requesting_user_id))

    # -------------------------------------------------------------------------
    # HOME MEMBERS
    # -------------------------------------------------------------------------
    def create_member(self, home_id: Any, requesting_user_id: Any, data: MemberCreate) -> Dict[str, Any]:
        return member_repository.create_member(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def get_home_members(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        return member_repository.get_home_members(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def get_member_by_id(self, member_id: Any, requesting_user_id: Any) -> Dict[str, Any]:
        return member_repository.get_member_by_id(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id))

    def update_member(self, member_id: Any, requesting_user_id: Any, data: MemberUpdate) -> Dict[str, Any]:
        return member_repository.update_member(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def delete_member(self, member_id: Any, requesting_user_id: Any) -> bool:
        return member_repository.delete_member(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id))

    # -------------------------------------------------------------------------
    # FACE RECORDS
    # -------------------------------------------------------------------------
    def create_face_record(self, member_id: Any, requesting_user_id: Any, data: FaceCreate) -> Dict[str, Any]:
        return face_repository.create_face_record(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def get_member_faces(self, member_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        return face_repository.get_member_faces(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id))

    def get_home_face_records(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        return face_repository.get_home_face_records(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def delete_face_record(self, face_id: Any, requesting_user_id: Any) -> bool:
        return face_repository.delete_face_record(face_id=_to_uuid(face_id), requesting_user_id=_to_uuid(requesting_user_id))

    def delete_member_faces(self, member_id: Any, requesting_user_id: Any) -> bool:
        return face_repository.delete_member_faces(member_id=_to_uuid(member_id), requesting_user_id=_to_uuid(requesting_user_id))

    # -------------------------------------------------------------------------
    # DEVICES
    # -------------------------------------------------------------------------
    def create_device(self, home_id: Any, requesting_user_id: Any, data: DeviceCreate) -> Dict[str, Any]:
        return device_repository.create_device(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def get_home_devices(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        return device_repository.get_home_devices(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def update_device(self, device_id: Any, requesting_user_id: Any, data: DeviceUpdate) -> Dict[str, Any]:
        return device_repository.update_device(device_id=_to_uuid(device_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def delete_device(self, device_id: Any, requesting_user_id: Any) -> bool:
        return device_repository.delete_device(device_id=_to_uuid(device_id), requesting_user_id=_to_uuid(requesting_user_id))

    # -------------------------------------------------------------------------
    # SECURITY LOGS
    # -------------------------------------------------------------------------
    def create_security_log(self, home_id: Any, requesting_user_id: Any, data: SecurityLogCreate) -> Dict[str, Any]:
        return security_log_repository.create_security_log(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def get_home_security_logs(
        self, home_id: Any, requesting_user_id: Any, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return security_log_repository.get_home_security_logs(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), event_type=event_type)

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------
    def create_alert(self, home_id: Any, requesting_user_id: Any, data: AlertCreate) -> Dict[str, Any]:
        return alert_repository.create_alert(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id), data=data)

    def get_home_alerts(self, home_id: Any, requesting_user_id: Any) -> List[Dict[str, Any]]:
        return alert_repository.get_home_alerts(home_id=_to_uuid(home_id), requesting_user_id=_to_uuid(requesting_user_id))

    def mark_alert_read(self, alert_id: Any, requesting_user_id: Any, is_read: bool = True) -> Dict[str, Any]:
        return alert_repository.mark_alert_read(alert_id=_to_uuid(alert_id), requesting_user_id=_to_uuid(requesting_user_id), is_read=is_read)

    def delete_alert(self, alert_id: Any, requesting_user_id: Any) -> bool:
        return alert_repository.delete_alert(alert_id=_to_uuid(alert_id), requesting_user_id=_to_uuid(requesting_user_id))


backend_store = BackendStore()

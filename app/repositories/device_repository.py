"""DeviceRepository: persistence for device records.

Phase 3A additions
------------------
``get_device_by_id_unchecked`` — internal PK lookup used by the device
  authentication dependency.  No user ownership is verified here; the
  caller (the dependency) is responsible for validating the credential.

``store_credential_hash`` — persists a bcrypt hash of the device's opaque
  bearer token immediately after a successful pairing claim.  The raw token
  is never passed to this method.

``revoke_device`` — owner-authenticated: clears ``credential_hash`` and
  sets ``status='revoked'``.  Takes effect immediately; the next device
  request will be rejected by the auth dependency.
"""
import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.models.device import DeviceCreate, DeviceUpdate
from app.repositories.home_repository import home_repository, is_supabase_configured, is_memory_fallback_enabled


class DeviceRepository:
    """Repository handling Device persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_devices: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        if not is_supabase_configured():
            if is_memory_fallback_enabled():
                return None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured; persistent device writes are unavailable.",
            )
        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service-role database access is unavailable; persistent writes are disabled.",
            )
        return client

    # ------------------------------------------------------------------
    # Existing CRUD operations (unchanged from pre-Phase-3A)
    # ------------------------------------------------------------------

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
                raise RuntimeError("Supabase returned no row after device insert")
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
            "credential_hash": None,
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
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device update was not applied.")
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

    # ------------------------------------------------------------------
    # Phase 3A — Device authentication support
    # ------------------------------------------------------------------

    def get_device_by_id_unchecked(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        """Return a device record by primary key WITHOUT checking user ownership.

        This method is exclusively for use by the device authentication
        dependency (``get_authenticated_device``).  It must NOT be used in
        user-facing endpoints — those must go through ``get_home_by_id`` +
        ownership verification.

        Returns ``None`` if the device does not exist (caller should treat
        this identically to an auth failure — do not distinguish 404 from
        bad-credential to avoid leaking information).

        Args:
            device_id: The device UUID parsed from the bearer token prefix.

        Returns:
            The device record dict, or ``None`` if not found.
        """
        client = self._get_client()
        if client:
            try:
                res = (
                    client.table("devices")
                    .select("id, home_id, status, credential_hash, device_name, device_type, device_identifier")
                    .eq("id", str(device_id))
                    .execute()
                )
                if not res.data:
                    return None
                row = res.data[0]
                row["id"] = UUID(row["id"]) if isinstance(row["id"], str) else row["id"]
                row["home_id"] = UUID(row["home_id"]) if isinstance(row["home_id"], str) else row["home_id"]
                return row
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during device authentication lookup: {exc}",
                ) from exc

        # In-memory path (isolated tests)
        return self._in_memory_devices.get(device_id)

    def get_device_session_state(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        """Read only the device identity, home, and status for session checks.

        This is intentionally separate from credential authentication: frame
        uploads need current revocation state, but must not fetch/verify the
        bcrypt credential hash on every frame.
        """
        client = self._get_client()
        if client:
            try:
                res = (
                    client.table("devices")
                    .select("id, home_id, status")
                    .eq("id", str(device_id))
                    .execute()
                )
                if not res.data:
                    return None
                row = res.data[0]
                return {
                    "id": UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
                    "home_id": UUID(row["home_id"]) if isinstance(row["home_id"], str) else row["home_id"],
                    "status": row.get("status"),
                }
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during device session status lookup: {exc}",
                ) from exc

        # In-memory path (isolated tests)
        device = self._in_memory_devices.get(device_id)
        if device is None:
            return None
        return {
            "id": device["id"],
            "home_id": device["home_id"],
            "status": device.get("status"),
        }

    def store_credential_hash(self, device_id: UUID, credential_hash: str) -> None:
        """Persist the bcrypt hash of a newly issued device credential.

        Called immediately after a successful pairing claim, before the raw
        token is returned to the caller.  The raw token MUST NOT be passed
        to this method — only the bcrypt hash.

        Raises HTTPException 500 on database failure (fails closed — never
        silently succeeds while leaving the hash unstored).

        Args:
            device_id: The UUID of the device that was just paired.
            credential_hash: The bcrypt hash of the token's secret portion.
        """
        client = self._get_client()
        if client:
            try:
                res = (
                    client.table("devices")
                    .update({"credential_hash": credential_hash})
                    .eq("id", str(device_id))
                    .execute()
                )
                if not res.data:
                    raise RuntimeError(
                        f"Supabase returned no rows after credential_hash update for device {device_id}. "
                        "The device record may not exist."
                    )
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error storing device credential hash: {exc}",
                ) from exc
            return

        # In-memory path (isolated tests)
        device = self._in_memory_devices.get(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Device {device_id} not found in memory store when storing credential hash.",
            )
        device["credential_hash"] = credential_hash

    def revoke_device(self, device_id: UUID, requesting_user_id: UUID) -> None:
        """Revoke a device's credential — owner-authenticated.

        Clears ``credential_hash`` and sets ``status='revoked'``.  The change
        takes effect immediately: the next request using the old token will be
        rejected by the ``get_authenticated_device`` dependency.

        Raises:
            HTTPException 404 — device not found.
            HTTPException 403 — requesting user does not own the device's home.
            HTTPException 500 — database error.

        Args:
            device_id: The UUID of the device to revoke.
            requesting_user_id: The authenticated user requesting revocation.
                Must own the home the device belongs to.
        """
        client = self._get_client()
        if client:
            try:
                # Ownership check: resolve home_id from device, then verify owner.
                res_dev = (
                    client.table("devices")
                    .select("home_id")
                    .eq("id", str(device_id))
                    .execute()
                )
                if not res_dev.data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Device not found.",
                    )
                home_id = UUID(res_dev.data[0]["home_id"])
                # Raises 403 if the requesting user does not own the home.
                home_repository.get_home_by_id(home_id, requesting_user_id)

                client.table("devices").update({
                    "status": "revoked",
                    "credential_hash": None,
                }).eq("id", str(device_id)).execute()

            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error revoking device: {exc}",
                ) from exc
            return

        # In-memory path (isolated tests)
        device = self._in_memory_devices.get(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found.",
            )
        # Ownership check
        home_repository.get_home_by_id(device["home_id"], requesting_user_id)
        device["status"] = "revoked"
        device["credential_hash"] = None


device_repository = DeviceRepository()

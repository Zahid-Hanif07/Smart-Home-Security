"""PairingRepository: persistence for one-time pairing codes and device registration.

Storage strategy
----------------
Production (Supabase configured):
    All writes go through the service-role admin client which bypasses RLS.
    The ``pairing_codes`` table is protected by its own RLS policies so that
    only the home owner can LIST their own codes.  The claim endpoint runs
    without an authenticated user, so it uses the admin client and performs
    all ownership validation server-side (never trusts client-supplied home_id).

Isolated tests (TEST_ISOLATED_MODE=1):
    Falls back to two in-memory dictionaries (codes + devices) so the entire
    test suite runs without a live Supabase connection.

Atomicity note
--------------
Supabase's PostgREST client does not expose raw transaction BEGIN/COMMIT.
The claim operation uses an optimistic update pattern:
  1. UPDATE pairing_codes SET is_used=TRUE … WHERE code=? AND is_used=FALSE
     AND expires_at > now()
  2. Inspect the number of rows updated.
     - 0 rows  → code is already used, expired, or missing (safe rejection).
     - 1 row   → this caller owns the claim; proceed to device upsert.
This pattern is race-safe because the WHERE clause on ``is_used=FALSE`` ensures
only one concurrent caller can transition the row to ``is_used=TRUE``.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.database.supabase_client import SupabaseClientManager
from app.repositories.home_repository import is_supabase_configured, is_memory_fallback_enabled


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


def _coerce_code_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise UUID string fields returned by Supabase."""
    for key in ("id", "home_id"):
        if record.get(key) and isinstance(record[key], str):
            record[key] = UUID(record[key])
    if record.get("device_id") and isinstance(record["device_id"], str):
        record["device_id"] = UUID(record["device_id"])
    return record


def _coerce_device_record(record: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("id", "home_id"):
        if record.get(key) and isinstance(record[key], str):
            record[key] = UUID(record[key])
    return record


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class PairingRepository:
    """Repository for pairing codes and the device records they create."""

    # Maximum active (unused, non-expired) codes allowed per home.
    MAX_ACTIVE_CODES_PER_HOME = 5

    def __init__(self) -> None:
        # In-memory stores for isolated tests only
        self._in_memory_codes: Dict[str, Dict[str, Any]] = {}   # keyed by code string
        self._in_memory_devices: Dict[UUID, Dict[str, Any]] = {}
        self._claim_lock = threading.Lock()  # serialises in-memory claims

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_admin_client(self):
        """Return the service-role Supabase client or raise 503."""
        if not is_supabase_configured():
            if is_memory_fallback_enabled():
                return None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured; pairing operations require a database connection.",
            )
        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service-role client is unavailable; pairing is temporarily disabled.",
            )
        return client

    # ------------------------------------------------------------------
    # Pairing-code creation
    # ------------------------------------------------------------------

    def count_active_codes(self, home_id: UUID) -> int:
        """Return the number of active (unused, non-expired) codes for a home."""
        client = self._get_admin_client()
        if client:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                res = (
                    client.table("pairing_codes")
                    .select("id", count="exact")
                    .eq("home_id", str(home_id))
                    .eq("is_used", False)
                    .gt("expires_at", now_iso)
                    .execute()
                )
                return res.count if res.count is not None else len(res.data or [])
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error counting active pairing codes: {exc}",
                ) from exc

        # In-memory fallback
        now = datetime.now(timezone.utc)
        return sum(
            1
            for c in self._in_memory_codes.values()
            if c["home_id"] == home_id
            and not c["is_used"]
            and c["expires_at"] > now
        )

    def create_code(
        self,
        home_id: UUID,
        code: str,
        expires_at: datetime,
    ) -> Dict[str, Any]:
        """Persist a newly generated pairing code.

        The caller is responsible for:
        - Verifying that the requesting user owns ``home_id``.
        - Checking active code counts before calling this method.
        - Generating a cryptographically secure ``code`` value.
        """
        client = self._get_admin_client()
        if client:
            try:
                row = {
                    "home_id": str(home_id),
                    "code": code,
                    "is_used": False,
                    "expires_at": expires_at.isoformat(),
                }
                res = client.table("pairing_codes").insert(row).execute()
                if res.data and len(res.data) > 0:
                    return _coerce_code_record(res.data[0])
                raise RuntimeError("Supabase returned no row after pairing_codes insert")
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating pairing code: {exc}",
                ) from exc

        # In-memory fallback
        record: Dict[str, Any] = {
            "id": uuid4(),
            "home_id": home_id,
            "code": code,
            "is_used": False,
            "expires_at": expires_at,
            "used_at": None,
            "device_id": None,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_codes[code] = record
        return record

    def list_active_codes(self, home_id: UUID) -> List[Dict[str, Any]]:
        """Return all non-expired, unused codes for a home (for informational use)."""
        client = self._get_admin_client()
        if client:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                res = (
                    client.table("pairing_codes")
                    .select("*")
                    .eq("home_id", str(home_id))
                    .eq("is_used", False)
                    .gt("expires_at", now_iso)
                    .order("created_at", desc=True)
                    .execute()
                )
                return [_coerce_code_record(r) for r in (res.data or [])]
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing pairing codes: {exc}",
                ) from exc

        now = datetime.now(timezone.utc)
        return [
            c
            for c in self._in_memory_codes.values()
            if c["home_id"] == home_id and not c["is_used"] and c["expires_at"] > now
        ]

    # ------------------------------------------------------------------
    # Pairing claim (atomic)
    # ------------------------------------------------------------------

    def claim_code(
        self,
        code: str,
        device_name: str,
        device_type: str,
        device_identifier: str,
    ) -> Dict[str, Any]:
        """Atomically claim a pairing code and register the calling device.

        Returns a dict with keys: device_id, home_id, device_name, device_type, status.

        Raises HTTPException:
            404 — code not found, already used, or expired.
            409 — device_identifier already registered to a *different* home.
            500 — unexpected database error.

        Security:
        - The home_id is taken exclusively from the persisted code record.
          The caller cannot supply or override it.
        - The optimistic UPDATE (is_used=FALSE → TRUE) prevents two simultaneous
          callers from both succeeding.
        """
        client = self._get_admin_client()
        if client:
            return self._claim_code_supabase(client, code, device_name, device_type, device_identifier)
        return self._claim_code_memory(code, device_name, device_type, device_identifier)

    # ---- Supabase path ----

    def _claim_code_supabase(
        self,
        client,
        code: str,
        device_name: str,
        device_type: str,
        device_identifier: str,
    ) -> Dict[str, Any]:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()

            # Step 1 — Atomic consume: set is_used only if currently unused AND not expired.
            update_res = (
                client.table("pairing_codes")
                .update({"is_used": True, "used_at": now_iso})
                .eq("code", code)
                .eq("is_used", False)
                .gt("expires_at", now_iso)
                .execute()
            )

            if not update_res.data:
                # Zero rows updated → code missing, already used, or expired.
                # Fetch to distinguish 404 vs 410 for a better error message.
                probe = (
                    client.table("pairing_codes")
                    .select("is_used, expires_at")
                    .eq("code", code)
                    .execute()
                )
                if not probe.data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pairing code not found. Please generate a new code from the mobile app.",
                    )
                row = probe.data[0]
                if row.get("is_used"):
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail="This pairing code has already been used. Please generate a new code.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This pairing code has expired. Please generate a new code from the mobile app.",
                )

            claimed_row = update_res.data[0]
            home_id = UUID(claimed_row["home_id"])

            # Step 2 — Check if device_identifier is already bound to a DIFFERENT home.
            existing_dev_res = (
                client.table("devices")
                .select("id, home_id, device_name, device_type")
                .eq("device_identifier", device_identifier)
                .execute()
            )
            if existing_dev_res.data:
                existing = existing_dev_res.data[0]
                existing_home = UUID(existing["home_id"])
                if existing_home != home_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "This device identifier is already registered to a different home. "
                            "Use a unique device_identifier or unpair the device first."
                        ),
                    )
                # Same home — already registered, idempotent success.
                device_id = UUID(existing["id"])
                # Update the pairing_codes row with the device_id reference.
                client.table("pairing_codes").update({"device_id": str(device_id)}).eq("code", code).execute()
                return {
                    "device_id": device_id,
                    "home_id": home_id,
                    "device_name": existing["device_name"],
                    "device_type": existing["device_type"],
                    "status": "already_registered",
                    "message": "Device was already registered to this home. Pairing code consumed.",
                }

            # Step 3 — Create new device record.
            dev_row = {
                "home_id": str(home_id),
                "device_name": device_name,
                "device_type": device_type,
                "device_identifier": device_identifier,
                "status": "offline",
                "paired_at": now_iso,
            }
            dev_res = client.table("devices").insert(dev_row).execute()
            if not dev_res.data:
                raise RuntimeError("Supabase returned no row after device insert during pairing claim")

            device = _coerce_device_record(dev_res.data[0])
            device_id = device["id"]

            # Step 4 — Link device_id back to the consumed code row.
            client.table("pairing_codes").update({"device_id": str(device_id)}).eq("code", code).execute()

            return {
                "device_id": device_id,
                "home_id": home_id,
                "device_name": device_name,
                "device_type": device_type,
                "status": "registered",
                "message": "Device successfully registered. It may now begin streaming for this home.",
            }

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error during pairing claim: {exc}",
            ) from exc

    # ---- In-memory path (isolated tests) ----

    def _claim_code_memory(
        self,
        code: str,
        device_name: str,
        device_type: str,
        device_identifier: str,
    ) -> Dict[str, Any]:
        with self._claim_lock:
            now = datetime.now(timezone.utc)
            record = self._in_memory_codes.get(code)

            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pairing code not found. Please generate a new code from the mobile app.",
                )
            if record["is_used"]:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This pairing code has already been used. Please generate a new code.",
                )
            if record["expires_at"] <= now:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This pairing code has expired. Please generate a new code from the mobile app.",
                )

            # Atomic consume
            record["is_used"] = True
            record["used_at"] = now
            home_id: UUID = record["home_id"]

            # Check for identifier registered to a different home
            for dev in self._in_memory_devices.values():
                if dev.get("device_identifier") == device_identifier:
                    if dev["home_id"] != home_id:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                "This device identifier is already registered to a different home. "
                                "Use a unique device_identifier or unpair the device first."
                            ),
                        )
                    # Same home — idempotent
                    record["device_id"] = dev["id"]
                    # Sync to device_repository so auth dependency can find it.
                    from app.repositories.device_repository import device_repository as _dev_repo
                    if dev["id"] not in _dev_repo._in_memory_devices:
                        _dev_repo._in_memory_devices[dev["id"]] = dict(dev)
                    return {
                        "device_id": dev["id"],
                        "home_id": home_id,
                        "device_name": dev["device_name"],
                        "device_type": dev["device_type"],
                        "status": "already_registered",
                        "message": "Device was already registered to this home. Pairing code consumed.",
                    }

            # Create new device
            device_id = uuid4()
            device: Dict[str, Any] = {
                "id": device_id,
                "home_id": home_id,
                "device_name": device_name,
                "device_type": device_type,
                "device_identifier": device_identifier,
                "status": "offline",
                "paired_at": now,
                "created_at": now,
                "last_seen": None,
            }
            self._in_memory_devices[device_id] = device
            record["device_id"] = device_id

            # Sync to device_repository so the auth dependency and
            # store_credential_hash can find this device by UUID.
            from app.repositories.device_repository import device_repository as _dev_repo
            _dev_repo._in_memory_devices[device_id] = device

            return {
                "device_id": device_id,
                "home_id": home_id,
                "device_name": device_name,
                "device_type": device_type,
                "status": "registered",
                "message": "Device successfully registered. It may now begin streaming for this home.",
            }

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset in-memory state for clean test execution."""
        self._in_memory_codes.clear()
        self._in_memory_devices.clear()


pairing_repository = PairingRepository()

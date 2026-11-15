import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database.supabase_client import SupabaseClientManager
from app.config.backend_settings import settings
from app.models.home import HomeCreate, HomeUpdate, HomeResponse


def is_supabase_configured() -> bool:
    """Check whether real Supabase credentials are configured in environment."""
    if os.getenv("TEST_ISOLATED_MODE") == "1" or os.getenv("USE_MOCK_DATABASE") == "1":
        return False
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_ANON_KEY
    if not url or "demo-project" in url or "your-project-id" in url:
        return False
    if not key or "dummy" in key or "your-supabase" in key:
        return False
    return True


def is_memory_fallback_enabled() -> bool:
    """Return True only when the in-memory test fallback is both requested and permitted.

    ``TEST_ISOLATED_MODE=1`` activates process-local storage for automated tests
    that must run without a live Supabase connection.  It is **exclusively for
    isolated automated tests** and must never be enabled on a production server.

    Safety guard
    ------------
    If ``ENVIRONMENT=production`` is set in the environment or ``.env`` file,
    this function raises ``RuntimeError`` immediately rather than silently
    allowing the in-memory fallback to mask missing production configuration.
    """  # noqa: D401
    if os.getenv("TEST_ISOLATED_MODE") != "1":
        return False

    # Deferred import to avoid circular dependency at module load time.
    from app.config.backend_settings import settings as _settings
    if _settings.ENVIRONMENT == "production":
        import logging
        _log = logging.getLogger(__name__)
        _log.critical(
            "FATAL CONFIGURATION ERROR: TEST_ISOLATED_MODE=1 is set but "
            "ENVIRONMENT=production. The in-memory fallback must not run in "
            "production — it silently discards all data. "
            "Remove TEST_ISOLATED_MODE from the production environment and "
            "ensure Supabase credentials are correctly configured."
        )
        raise RuntimeError(
            "TEST_ISOLATED_MODE=1 is not permitted when ENVIRONMENT=production. "
            "Remove this environment variable from your production deployment."
        )

    return True


class HomeRepository:
    """Repository handling Home entity persistence via Supabase PostgreSQL or in-memory fallback."""

    def __init__(self):
        self._in_memory_homes: Dict[UUID, Dict[str, Any]] = {}

    def _get_client(self):
        if not is_supabase_configured():
            if is_memory_fallback_enabled():
                return None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured; persistent database writes are unavailable.",
            )
        client = SupabaseClientManager.get_admin_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service-role database access is unavailable; persistent writes are disabled.",
            )
        return client

    def create_home(self, owner_id: UUID, data: HomeCreate) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                home_data = {
                    "owner_id": str(owner_id),
                    "name": data.name,
                    "address": data.address,
                }
                res = client.table("homes").insert(home_data).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    record["id"] = UUID(record["id"]) if isinstance(record["id"], str) else record["id"]
                    record["owner_id"] = UUID(record["owner_id"]) if isinstance(record["owner_id"], str) else record["owner_id"]
                    return record
                raise RuntimeError("Supabase returned no row after home insert")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error creating home: {str(e)}",
                )

        # In-memory mode for tests or unconfigured dev environment
        home_id = uuid4()
        home = {
            "id": home_id,
            "owner_id": owner_id,
            "name": data.name,
            "address": data.address,
            "created_at": datetime.now(timezone.utc),
        }
        self._in_memory_homes[home_id] = home
        return home

    def ensure_initial_home(self, owner_id: UUID, name: str = "Main Residence") -> Dict[str, Any]:
        """Return an existing home or create one marked as the owner's initial home.

        The partial unique index added by the accompanying migration serializes
        concurrent initial-home attempts. Existing homes are reused, never removed.
        """
        client = self._get_client()
        if client:
            try:
                existing = client.table("homes").select("*").eq("owner_id", str(owner_id)).order("created_at").limit(1).execute()
                if existing.data:
                    item = existing.data[0]
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["owner_id"] = UUID(item["owner_id"]) if isinstance(item["owner_id"], str) else item["owner_id"]
                    return item
                res = client.table("homes").insert({
                    "owner_id": str(owner_id),
                    "name": name,
                    "address": None,
                    "is_initial": True,
                }).execute()
                if res.data:
                    item = res.data[0]
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["owner_id"] = UUID(item["owner_id"]) if isinstance(item["owner_id"], str) else item["owner_id"]
                    return item
                raise RuntimeError("Supabase returned no row after initial-home insert")
            except Exception as exc:
                # A concurrent request may have won the partial unique index race.
                try:
                    existing = client.table("homes").select("*").eq("owner_id", str(owner_id)).order("created_at").limit(1).execute()
                    if existing.data:
                        item = existing.data[0]
                        item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                        item["owner_id"] = UUID(item["owner_id"]) if isinstance(item["owner_id"], str) else item["owner_id"]
                        return item
                except Exception:
                    pass
                if isinstance(exc, HTTPException):
                    raise
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error ensuring initial home: {exc}",
                ) from exc

        existing = sorted(
            (h for h in self._in_memory_homes.values() if h["owner_id"] == owner_id),
            key=lambda h: h["created_at"],
        )
        if existing:
            return existing[0]
        home_id = uuid4()
        home = {
            "id": home_id,
            "owner_id": owner_id,
            "name": name,
            "address": None,
            "created_at": datetime.now(timezone.utc),
            "is_initial": True,
        }
        self._in_memory_homes[home_id] = home
        return home

    def get_user_homes(self, owner_id: UUID) -> List[Dict[str, Any]]:
        client = self._get_client()
        if client:
            try:
                res = client.table("homes").select("*").eq("owner_id", str(owner_id)).execute()
                homes = []
                for item in res.data or []:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]
                    item["owner_id"] = UUID(item["owner_id"]) if isinstance(item["owner_id"], str) else item["owner_id"]
                    homes.append(item)
                return homes
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error listing homes: {str(e)}",
                )

        return [h for h in self._in_memory_homes.values() if h["owner_id"] == owner_id]

    def get_home_by_id(self, home_id: UUID, requesting_user_id: UUID) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                res = client.table("homes").select("*").eq("id", str(home_id)).execute()
                if not res.data or len(res.data) == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home not found.")
                home = res.data[0]
                owner_uuid = UUID(home["owner_id"]) if isinstance(home["owner_id"], str) else home["owner_id"]
                if owner_uuid != requesting_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. You do not own this home.",
                    )
                home["id"] = UUID(home["id"]) if isinstance(home["id"], str) else home["id"]
                home["owner_id"] = owner_uuid
                return home
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error fetching home: {str(e)}",
                )

        home = self._in_memory_homes.get(home_id)
        if not home:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home not found.")
        if home["owner_id"] != requesting_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this home.",
            )
        return home

    def update_home(self, home_id: UUID, requesting_user_id: UUID, data: HomeUpdate) -> Dict[str, Any]:
        home = self.get_home_by_id(home_id, requesting_user_id)
        client = self._get_client()
        if client:
            try:
                update_data = {}
                if data.name is not None:
                    update_data["name"] = data.name
                if data.address is not None:
                    update_data["address"] = data.address
                if not update_data:
                    return home

                res = client.table("homes").update(update_data).eq("id", str(home_id)).execute()
                if res.data and len(res.data) > 0:
                    updated = res.data[0]
                    updated["id"] = UUID(updated["id"]) if isinstance(updated["id"], str) else updated["id"]
                    updated["owner_id"] = UUID(updated["owner_id"]) if isinstance(updated["owner_id"], str) else updated["owner_id"]
                    return updated
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home update was not applied.")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error updating home: {str(e)}",
                )

        if data.name is not None:
            home["name"] = data.name
        if data.address is not None:
            home["address"] = data.address
        return home

    def delete_home(self, home_id: UUID, requesting_user_id: UUID) -> bool:
        home = self.get_home_by_id(home_id, requesting_user_id)
        client = self._get_client()
        if client:
            try:
                client.table("homes").delete().eq("id", str(home_id)).execute()
                return True
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error deleting home: {str(e)}",
                )

        if home_id in self._in_memory_homes:
            del self._in_memory_homes[home_id]
        return True


home_repository = HomeRepository()

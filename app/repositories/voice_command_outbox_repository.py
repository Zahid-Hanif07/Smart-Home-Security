from __future__ import annotations

from typing import Any, List

from app.database.supabase_client import SupabaseClientManager
from app.services.voice_command_outbox_worker import DEFAULT_LEASE_SECONDS, MockDeliveryOutcome, OutboxJob


class VoiceCommandOutboxRepository:
    """Production repository; each operation is one database RPC transaction."""

    def __init__(self, client_factory=None):
        self._client_factory = client_factory or SupabaseClientManager.get_admin_client

    def claim_pending(self, worker_id: str, limit: int = 10, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> List[OutboxJob]:
        client = self._client_factory()
        if not client:
            raise RuntimeError("Supabase admin client unavailable")
        response = client.rpc("claim_voice_command_outbox", {
            "p_worker_id": worker_id,
            "p_limit": limit,
            "p_lease_seconds": lease_seconds,
        }).execute()
        return [OutboxJob.from_mapping(item) for item in (response.data or [])]

    def recover_expired(self) -> int:
        client = self._client_factory()
        if not client:
            raise RuntimeError("Supabase admin client unavailable")
        response = client.rpc("recover_voice_command_outbox", {}).execute()
        return int(response.data or 0)

    def complete(self, job: OutboxJob, worker_id: str, outcome: MockDeliveryOutcome) -> bool:
        client = self._client_factory()
        if not client:
            raise RuntimeError("Supabase admin client unavailable")
        try:
            response = client.rpc("complete_voice_command_outbox", {
                "p_outbox_id": str(job.outbox_id),
                "p_worker_id": worker_id,
                "p_delivery_id": str(job.delivery_id),
                "p_outcome": outcome.value,
            }).execute()
        except Exception as exc:
            if "stale_lease" in str(exc):
                return False
            raise
        return bool(response.data)

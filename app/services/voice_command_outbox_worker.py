from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Iterable, List, Optional, Protocol
from uuid import UUID


DEFAULT_LEASE_SECONDS = 60
MAX_ATTEMPTS = 5


class MockDeliveryOutcome(str, Enum):
    SUCCESS = "success"
    OFFLINE = "offline"
    PERMANENT_FAILURE = "permanent_failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class OutboxJob:
    outbox_id: UUID
    command_id: UUID
    home_id: UUID
    device_id: UUID
    result_id: UUID
    delivery_id: UUID
    expires_at: datetime
    next_attempt_at: Optional[datetime] = None
    attempt_count: int = 0
    outbox_state: str = "pending"
    result_status: str = "pending"
    worker_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    terminal_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    command_status: str = "accepted"
    command_terminal_at: Optional[datetime] = None

    @classmethod
    def from_mapping(cls, value: dict) -> "OutboxJob":
        return cls(
            outbox_id=UUID(str(value["outbox_id"])),
            command_id=UUID(str(value["command_id"])),
            home_id=UUID(str(value["home_id"])),
            device_id=UUID(str(value["device_id"])),
            result_id=UUID(str(value["result_id"])),
            delivery_id=UUID(str(value["delivery_id"])),
            expires_at=value["expires_at"] if isinstance(value["expires_at"], datetime)
            else datetime.fromisoformat(str(value["expires_at"]).replace("Z", "+00:00")),
            attempt_count=int(value.get("attempt_count", 0)),
        )


class OutboxRepository(Protocol):
    def claim_pending(self, worker_id: str, limit: int = 10, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> List[OutboxJob]: ...
    def recover_expired(self) -> int: ...
    def complete(self, job: OutboxJob, worker_id: str, outcome: MockDeliveryOutcome) -> bool: ...


class MockDeviceAdapter:
    """Deterministic, local-only adapter. It never sends a device command."""

    def __init__(self, outcomes: Optional[Iterable[MockDeliveryOutcome]] = None):
        self._outcomes = list(outcomes or [MockDeliveryOutcome.SUCCESS])
        self.calls: List[UUID] = []
        self._results: Dict[UUID, MockDeliveryOutcome] = {}

    def process(self, delivery_id: UUID) -> MockDeliveryOutcome:
        if delivery_id in self._results:
            return self._results[delivery_id]
        self.calls.append(delivery_id)
        if self._outcomes:
            outcome = self._outcomes.pop(0)
        else:
            outcome = MockDeliveryOutcome.SUCCESS
        self._results[delivery_id] = outcome
        return outcome


class InMemoryOutboxRepository:
    """Isolated-test repository with the same claim/lease contract as SQL."""

    def __init__(self):
        import threading
        self._lock = threading.RLock()
        self.jobs: Dict[UUID, OutboxJob] = {}

    def seed(self, job: OutboxJob) -> None:
        with self._lock:
            self.jobs[job.outbox_id] = job

    def recover_expired(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        recovered = 0
        with self._lock:
            changed = []
            for job in self.jobs.values():
                if job.outbox_state != "processing" or not job.lease_expires_at or job.lease_expires_at >= now:
                    continue
                job.worker_id = None
                job.lease_expires_at = None
                if job.result_status == "failed":
                    job.outbox_state = "failed"
                elif job.attempt_count < MAX_ATTEMPTS and now < job.expires_at:
                    job.outbox_state = "pending"
                    job.next_attempt_at = now + _backoff(job.attempt_count)
                    recovered += 1
                else:
                    job.outbox_state = "failed"
                    if job.result_status != "failed":
                        job.result_status = "timed_out"
                        job.terminal_at = now
                changed.append(job)
            for job in changed:
                self._recompute_command(job, now)
        return recovered

    def claim_pending(self, worker_id: str, limit: int = 10, lease_seconds: int = DEFAULT_LEASE_SECONDS, now: Optional[datetime] = None) -> List[OutboxJob]:
        now = now or datetime.now(timezone.utc)
        with self._lock:
            self.recover_expired(now)
            candidates = sorted(
                (job for job in self.jobs.values()
                 if job.outbox_state == "pending"
                 and job.attempt_count < MAX_ATTEMPTS
                 and (job.next_attempt_at is None or job.next_attempt_at <= now)
                 and job.expires_at > now),
                key=lambda job: (str(job.home_id), str(job.device_id), str(job.result_id)),
            )[:limit]
            claimed = []
            for job in candidates:
                job.attempt_count += 1
                job.outbox_state = "processing"
                job.worker_id = worker_id
                job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                claimed.append(job)
            for job in claimed:
                self._recompute_command(job, now)
            return claimed

    def complete(self, job: OutboxJob, worker_id: str, outcome: MockDeliveryOutcome, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        with self._lock:
            current = self.jobs.get(job.outbox_id)
            if current is None or current.delivery_id != job.delivery_id:
                return False
            if current.result_status == "acknowledged" and outcome == MockDeliveryOutcome.SUCCESS:
                return True
            if current.outbox_state != "processing" or current.worker_id != worker_id:
                return False
            if current.lease_expires_at is None or current.lease_expires_at <= now:
                return False

            current.worker_id = None
            current.lease_expires_at = None
            if outcome == MockDeliveryOutcome.SUCCESS:
                current.result_status = "acknowledged"
                current.outbox_state = "completed"
                current.terminal_at = now
            elif outcome == MockDeliveryOutcome.UNKNOWN:
                current.result_status = "unknown_outcome"
                current.outbox_state = "failed"
            elif outcome == MockDeliveryOutcome.PERMANENT_FAILURE:
                current.result_status = "failed"
                current.outbox_state = "failed"
                current.terminal_at = now
            elif current.attempt_count < MAX_ATTEMPTS and now < current.expires_at:
                current.result_status = "device_offline" if outcome == MockDeliveryOutcome.OFFLINE else "timed_out"
                current.outbox_state = "pending"
                current.next_attempt_at = now + _backoff(current.attempt_count)
            else:
                current.result_status = "device_offline" if outcome == MockDeliveryOutcome.OFFLINE else "timed_out"
                current.outbox_state = "failed"
                current.terminal_at = now
            self._recompute_command(current, now)
            return True

    def _recompute_command(self, changed: OutboxJob, now: datetime) -> None:
        jobs = [job for job in self.jobs.values() if job.command_id == changed.command_id]
        if not jobs:
            return
        if any(job.result_status == "unknown_outcome" for job in jobs):
            status = "unknown_outcome"
            terminal_at = None
        elif all(job.result_status == "acknowledged" for job in jobs):
            status = "acknowledged"
            terminal_at = now
        elif any(job.outbox_state in {"pending", "processing"} for job in jobs):
            status = "dispatched"
            terminal_at = None
        elif any(job.result_status == "acknowledged" for job in jobs):
            status = "partially_acknowledged"
            terminal_at = now
        elif any(job.result_status == "timed_out" for job in jobs):
            status = "timed_out"
            terminal_at = now
        else:
            status = "failed"
            terminal_at = now
        for job in jobs:
            job.command_status = status
            job.command_terminal_at = terminal_at


def _backoff(attempt_count: int) -> timedelta:
    return timedelta(seconds=min(60, 2 ** max(1, attempt_count)))


class VoiceCommandOutboxWorker:
    def __init__(self, repository: OutboxRepository, adapter: MockDeviceAdapter, worker_id: str, lease_seconds: int = DEFAULT_LEASE_SECONDS):
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.repository = repository
        self.adapter = adapter
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds

    def run_once(self, limit: int = 10) -> int:
        self.repository.recover_expired()
        jobs = self.repository.claim_pending(self.worker_id, limit=limit, lease_seconds=self.lease_seconds)
        for job in jobs:
            outcome = self.adapter.process(job.delivery_id)
            self.repository.complete(job, self.worker_id, outcome)
        return len(jobs)

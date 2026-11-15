from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread
from uuid import uuid4

import pytest

from app.repositories.voice_command_outbox_repository import VoiceCommandOutboxRepository
from app.services.voice_command_outbox_worker import (
    InMemoryOutboxRepository,
    MockDeliveryOutcome,
    MockDeviceAdapter,
    OutboxJob,
    VoiceCommandOutboxWorker,
)


def job(expires=None, command_id=None):
    return OutboxJob(
        outbox_id=uuid4(), command_id=command_id or uuid4(), home_id=uuid4(), device_id=uuid4(),
        result_id=uuid4(), delivery_id=uuid4(),
        expires_at=expires or datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def test_pending_job_can_be_claimed_with_lease():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    claimed = repo.claim_pending("worker-a")
    assert claimed == [item]
    assert item.outbox_state == "processing"
    assert item.worker_id == "worker-a"
    assert item.lease_expires_at is not None
    assert item.attempt_count == 1


def test_two_workers_cannot_claim_same_job():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    barrier = Barrier(2)
    results = []

    def claim(worker):
        barrier.wait()
        results.append(repo.claim_pending(worker))

    threads = [Thread(target=claim, args=(f"worker-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(len(result) for result in results) == 1


def test_expired_lease_is_recovered_without_resetting_attempts():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    repo.claim_pending("worker-a")
    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert repo.recover_expired() == 1
    assert item.outbox_state == "pending"
    assert item.attempt_count == 1


def test_stale_worker_cannot_update_after_recovery():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    stale = repo.claim_pending("worker-a")[0]
    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    repo.recover_expired()
    item.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    current = repo.claim_pending("worker-b")[0]
    assert not repo.complete(stale, "worker-a", MockDeliveryOutcome.SUCCESS)
    assert repo.complete(current, "worker-b", MockDeliveryOutcome.SUCCESS)


def test_completion_after_lease_expiry_is_rejected():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    claimed = repo.claim_pending("worker")[0]
    expired = claimed.lease_expires_at + timedelta(seconds=1)
    assert not repo.complete(claimed, "worker", MockDeliveryOutcome.SUCCESS, expired)
    assert item.result_status == "pending"


def test_completion_before_lease_expiry_succeeds():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    claimed = repo.claim_pending("worker")[0]
    before_expiry = claimed.lease_expires_at - timedelta(seconds=1)
    assert repo.complete(claimed, "worker", MockDeliveryOutcome.SUCCESS, before_expiry)
    assert item.result_status == "acknowledged"


def test_attempt_count_never_exceeds_five():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    for _ in range(5):
        claimed = repo.claim_pending("worker")
        assert claimed
        item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        repo.recover_expired()
        item.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert item.attempt_count == 5
    assert repo.claim_pending("worker") == []


def test_delivery_id_survives_retries():
    repo = InMemoryOutboxRepository()
    item = job()
    delivery_id = item.delivery_id
    repo.seed(item)
    claimed = repo.claim_pending("worker")[0]
    assert claimed.delivery_id == delivery_id
    repo.complete(claimed, "worker", MockDeliveryOutcome.OFFLINE)
    item.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    retry = repo.claim_pending("worker")[0]
    assert retry.delivery_id == delivery_id


def test_mock_success_records_acknowledgement():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    worker = VoiceCommandOutboxWorker(repo, MockDeviceAdapter(), "worker")
    assert worker.run_once() == 1
    assert item.result_status == "acknowledged"
    assert item.outbox_state == "completed"
    assert item.terminal_at is not None


def test_claim_updates_aggregate_status_to_dispatched():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    assert repo.claim_pending("worker") == [item]
    assert item.command_status == "dispatched"


def test_temporary_offline_schedules_retry():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    worker = VoiceCommandOutboxWorker(repo, MockDeviceAdapter([MockDeliveryOutcome.OFFLINE]), "worker")
    worker.run_once()
    assert item.result_status == "device_offline"
    assert item.outbox_state == "pending"
    assert item.next_attempt_at is not None


def test_permanent_failure_is_terminal():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    worker = VoiceCommandOutboxWorker(repo, MockDeviceAdapter([MockDeliveryOutcome.PERMANENT_FAILURE]), "worker")
    worker.run_once()
    assert item.result_status == "failed"
    assert item.outbox_state == "failed"
    assert item.terminal_at is not None


@pytest.mark.parametrize("outcome", [MockDeliveryOutcome.TIMEOUT, MockDeliveryOutcome.UNKNOWN])
def test_timeout_and_unknown_outcome_are_not_acknowledged(outcome):
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    worker = VoiceCommandOutboxWorker(repo, MockDeviceAdapter([outcome]), "worker")
    worker.run_once()
    assert item.result_status in {"timed_out", "unknown_outcome"}
    assert item.result_status != "acknowledged"


def test_expired_command_is_not_dispatched():
    repo = InMemoryOutboxRepository()
    item = job(datetime.now(timezone.utc) - timedelta(seconds=1))
    repo.seed(item)
    assert repo.claim_pending("worker") == []
    assert item.attempt_count == 0


def test_duplicate_processing_is_idempotent():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    claimed = repo.claim_pending("worker")[0]
    assert repo.complete(claimed, "worker", MockDeliveryOutcome.SUCCESS)
    assert repo.complete(claimed, "worker", MockDeliveryOutcome.SUCCESS)
    assert item.attempt_count == 1


def test_database_repository_surfaces_client_errors():
    class BrokenClient:
        def rpc(self, *_args, **_kwargs):
            raise RuntimeError("database unavailable")

    repo = VoiceCommandOutboxRepository(lambda: BrokenClient())
    with pytest.raises(RuntimeError, match="database unavailable"):
        repo.claim_pending("worker")


def test_production_repository_normalizes_claimed_job():
    item = job()

    class Response:
        data = [{
            "outbox_id": str(item.outbox_id),
            "command_id": str(item.command_id),
            "home_id": str(item.home_id),
            "device_id": str(item.device_id),
            "result_id": str(item.result_id),
            "delivery_id": str(item.delivery_id),
            "attempt_count": 1,
            "expires_at": item.expires_at.isoformat(),
        }]

    class Rpc:
        def execute(self):
            return Response()

    class Client:
        def rpc(self, name, payload):
            assert name == "claim_voice_command_outbox"
            assert payload["p_lease_seconds"] == 60
            return Rpc()

    claimed = VoiceCommandOutboxRepository(lambda: Client()).claim_pending("worker")
    assert claimed[0].delivery_id == item.delivery_id
    assert claimed[0].attempt_count == 1


def test_production_repository_maps_stale_lease_to_false():
    item = job()

    class BrokenRpc:
        def execute(self):
            raise RuntimeError("stale_lease")

    class Client:
        def rpc(self, name, payload):
            assert name == "complete_voice_command_outbox"
            return BrokenRpc()

    result = VoiceCommandOutboxRepository(lambda: Client()).complete(
        item, "worker", MockDeliveryOutcome.SUCCESS
    )
    assert result is False


def test_mock_adapter_deduplicates_delivery_id():
    delivery_id = uuid4()
    adapter = MockDeviceAdapter([MockDeliveryOutcome.OFFLINE, MockDeliveryOutcome.SUCCESS])
    first = adapter.process(delivery_id)
    second = adapter.process(delivery_id)
    assert first == second == MockDeliveryOutcome.OFFLINE
    assert adapter.calls == [delivery_id]


def test_permanent_failure_is_not_rewritten_by_recovery():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    repo.claim_pending("worker")
    item.result_status = "failed"
    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    repo.recover_expired()
    assert item.result_status == "failed"
    assert item.outbox_state == "failed"


def test_recovery_schedules_bounded_backoff():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    repo.claim_pending("worker")
    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    before = datetime.now(timezone.utc)
    assert repo.recover_expired(before) == 1
    assert item.next_attempt_at is not None
    assert item.next_attempt_at > before


def test_aggregate_status_is_recomputed_for_multiple_devices():
    repo = InMemoryOutboxRepository()
    command_id = uuid4()
    first, second = job(command_id=command_id), job(command_id=command_id)
    repo.seed(first)
    repo.seed(second)
    worker = VoiceCommandOutboxWorker(
        repo,
        MockDeviceAdapter([MockDeliveryOutcome.SUCCESS, MockDeliveryOutcome.PERMANENT_FAILURE]),
        "worker",
    )
    assert worker.run_once(limit=2) == 2
    assert first.command_status == "partially_acknowledged"
    assert second.command_status == "partially_acknowledged"


def test_unknown_outcome_remains_unresolved():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    worker = VoiceCommandOutboxWorker(repo, MockDeviceAdapter([MockDeliveryOutcome.UNKNOWN]), "worker")
    worker.run_once()
    assert item.command_status == "unknown_outcome"
    assert item.command_terminal_at is None


def test_repeated_recovery_never_allows_sixth_attempt():
    repo = InMemoryOutboxRepository()
    item = job()
    repo.seed(item)
    for _ in range(5):
        assert repo.claim_pending("worker")
        item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        repo.recover_expired()
        item.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert item.attempt_count == 5
    assert repo.claim_pending("worker") == []

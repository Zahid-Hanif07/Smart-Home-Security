import numpy as np

from app.security.stream_integrity_service import StreamIntegrityService
from app.security.evidence_store import EvidenceStore


def test_failed_camera_read_is_reported():
    service = StreamIntegrityService()
    events = service.inspect(None, read_ok=False)
    assert [event["event_type"] for event in events] == ["camera_read_failure"]


def test_stale_frame_timestamp_is_reported():
    service = StreamIntegrityService(stale_after_seconds=2)
    frame = np.full((64, 64, 3), 120, dtype=np.uint8)
    events = service.inspect(frame, captured_at=1.0, now=5.0)
    assert "stream_stale" in [event["event_type"] for event in events]


def test_static_scene_is_not_reported_as_replay_or_frozen():
    service = StreamIntegrityService(repeated_sequence_length=3, replay_repeats=2)
    frame = np.full((64, 64, 3), 120, dtype=np.uint8)
    observed = []
    for index in range(30):
        observed.extend(service.inspect(frame, captured_at=index / 10, now=index / 10))
    assert not any(event["event_type"] in {"replay_suspected", "stream_frozen"} for event in observed)
    assert service.identical_frame_count > 0


def test_repeated_multi_frame_sequence_is_only_a_suspicion():
    service = StreamIntegrityService(repeated_sequence_length=3, replay_repeats=3)
    frames = [
        np.zeros((64, 64, 3), dtype=np.uint8),
        np.tile(np.arange(64, dtype=np.uint8)[None, :, None], (64, 1, 3)),
        np.tile(np.arange(64, dtype=np.uint8)[:, None, None], (1, 64, 3)),
    ]
    events = []
    for index in range(9):
        events.extend(service.inspect(frames[index % 3], captured_at=index / 10, now=index / 10))
    replay = [event for event in events if event["event_type"] == "replay_suspected"]
    assert replay
    assert "not proof" in replay[0]["reason"]


def test_obstruction_is_reported_as_uncertain_after_sustained_dark_frames():
    service = StreamIntegrityService()
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    events = []
    for index in range(35):
        events.extend(service.inspect(frame, captured_at=index / 10, now=index / 10))
    obstruction = [event for event in events if event["event_type"] == "possible_camera_obstruction"]
    assert obstruction
    assert "legitimate" in obstruction[0]["reason"]


def test_evidence_store_uses_home_scoped_storage_keys(tmp_path):
    store = EvidenceStore(tmp_path)
    home_id = "home-test-id"
    key = store.save_frame(home_id, np.full((32, 32, 3), 180, dtype=np.uint8))
    assert key is not None and "/" not in key and "\\" not in key
    assert store.resolve(home_id, key) is not None
    assert store.resolve("another-home", key) is None
    assert store.resolve(home_id, "..\\secret.jpg") is None

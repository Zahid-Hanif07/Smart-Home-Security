import threading
import time

import numpy as np

from app.security.face_occlusion_runtime import (
    FaceOcclusionDiagnostic,
    STATUS_FAILED,
    STATUS_INVALID,
    STATUS_REPLACED,
    STATUS_SUCCESS,
    STATUS_STALE,
    STATUS_UNAVAILABLE,
    FaceOcclusionRuntime,
)
from app.security.face_occlusion_service import FaceOcclusionResult, FaceOcclusionService
from app.security.security_service import SecurityService


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def face(x=8, y=8, width=24, height=24):
    return {"box": (x, y, width, height), "confidence": 0.9}


def successful_result():
    return FaceOcclusionResult(
        state="segmentation_available",
        reason="segmentation_completed",
        mode="direct_crop",
    )


class BlockingService:
    started = threading.Event()
    release = threading.Event()
    calls = []

    def __init__(self, _model_path):
        pass

    def evaluate(self, crop, **_kwargs):
        type(self).calls.append(crop.copy())
        type(self).started.set()
        type(self).release.wait(timeout=2)
        return successful_result()


class FastService:
    calls = []

    def __init__(self, _model_path):
        pass

    def evaluate(self, crop, **_kwargs):
        type(self).calls.append(crop.copy())
        return successful_result()


class FailingService:
    def __init__(self, _model_path):
        pass

    def evaluate(self, _crop, **_kwargs):
        raise RuntimeError("synthetic inference failure")


def start_runtime(service_factory):
    runtime = FaceOcclusionRuntime(service_factory=service_factory)
    runtime.start()
    return runtime


def submit_one(runtime, sequence=15, frame=None, detected=None):
    frame = np.full((64, 64, 3), 120, dtype=np.uint8) if frame is None else frame
    detected = [face()] if detected is None else detected
    return runtime.submit_faces(frame, sequence, detected)


def test_runtime_starts_and_loads_model_only_inside_worker():
    threads = []
    ready = threading.Event()

    def factory(model_path):
        threads.append((threading.current_thread().name, model_path))
        ready.set()
        return FastService(model_path)

    runtime = FaceOcclusionRuntime(service_factory=factory)
    assert threads == []
    runtime.start()
    assert ready.wait(1.0)
    assert threads[0][0] == "faceocc-worker"
    runtime.stop()
    assert not runtime.is_running


def test_environment_model_path_is_used(monkeypatch, tmp_path):
    configured_path = tmp_path / "configured-faceocc.onnx"
    monkeypatch.setenv("FACEOCC_MODEL_PATH", str(configured_path))
    runtime = FaceOcclusionRuntime(service_factory=FastService)
    assert runtime.model_path == configured_path


def test_explicit_configured_model_path_is_preserved(tmp_path):
    configured_path = tmp_path / "explicit-faceocc.onnx"
    runtime = FaceOcclusionRuntime(
        model_path=configured_path,
        service_factory=FastService,
    )
    assert runtime.model_path == configured_path


def test_fresh_result_is_accepted_and_expired_result_is_stale():
    runtime = FaceOcclusionRuntime(service_factory=FastService, max_result_age_seconds=2.0)
    fresh = FaceOcclusionDiagnostic(15, 0, (0, 0, 1, 1), 98.5, 99.0, STATUS_SUCCESS, "fresh")
    expired = FaceOcclusionDiagnostic(15, 0, (0, 0, 1, 1), 96.0, 97.0, STATUS_SUCCESS, "expired")
    assert not runtime.is_stale(fresh, max_age_seconds=2.0, now=100.0)
    assert runtime.is_stale(expired, max_age_seconds=2.0, now=100.0)
    assert runtime.mark_stale(expired).status == STATUS_STALE


def test_missing_or_invalid_timestamp_is_stale():
    runtime = FaceOcclusionRuntime(service_factory=FastService)
    for timestamp in (None, "not-a-timestamp"):
        diagnostic = FaceOcclusionDiagnostic(
            15, 0, (0, 0, 1, 1), 99.0, timestamp, STATUS_SUCCESS, "timestamp"
        )
        assert runtime.is_stale(diagnostic, max_age_seconds=2.0, now=100.0)


def test_older_sequence_submission_is_rejected():
    runtime = start_runtime(FastService)
    try:
        assert submit_one(runtime, 30) == "queued"
        assert submit_one(runtime, 15) == "dropped_old"
    finally:
        runtime.stop()


def test_queue_replaces_old_pending_batch_and_never_exceeds_one():
    BlockingService.started.clear()
    BlockingService.release.clear()
    BlockingService.calls.clear()
    runtime = start_runtime(BlockingService)
    try:
        assert submit_one(runtime, 15) == "queued"
        assert BlockingService.started.wait(1.0)
        assert submit_one(runtime, 30) == "queued"
        assert submit_one(runtime, 45) == STATUS_REPLACED
        BlockingService.release.set()
        assert wait_until(lambda: len(runtime.get_results()) == 2)
        assert {item.frame_sequence for item in runtime.get_results()} == {15, 45}
    finally:
        BlockingService.release.set()
        runtime.stop()


def test_crop_is_copied_before_worker_can_mutate_it():
    class MutatingService(FastService):
        def evaluate(self, crop, **kwargs):
            crop[:] = 0
            return successful_result()

    frame = np.full((64, 64, 3), 123, dtype=np.uint8)
    runtime = start_runtime(MutatingService)
    try:
        assert submit_one(runtime, 15, frame=frame) == "queued"
        assert wait_until(lambda: runtime.get_result(15, 0) is not None)
        assert np.all(frame[8:32, 8:32] == 123)
    finally:
        runtime.stop()


def test_multiple_faces_keep_frame_face_and_box_association():
    FastService.calls.clear()
    runtime = start_runtime(FastService)
    detected = [face(2, 3, 20, 21), face(35, 30, 22, 25)]
    try:
        assert submit_one(runtime, 15, detected=detected) == "queued"
        assert wait_until(lambda: len(runtime.get_results(frame_sequence=15)) == 2)
        results = runtime.get_results(frame_sequence=15)
        assert {(item.face_index, item.box) for item in results} == {
            (0, (2, 3, 20, 21)),
            (1, (35, 30, 22, 25)),
        }
    finally:
        runtime.stop()


def test_missing_model_is_unavailable():
    runtime = FaceOcclusionRuntime(
        model_path="missing-faceocc-runtime.onnx",
        service_factory=FaceOcclusionService,
    )
    try:
        runtime.start()
        assert submit_one(runtime, 15) == "queued"
        assert wait_until(lambda: runtime.get_result(15, 0) is not None)
        result = runtime.get_result(15, 0)
        assert result.status == STATUS_UNAVAILABLE
        assert result.reason == "model_file_missing"
    finally:
        runtime.stop()


def test_invalid_crop_is_explicit_and_does_not_call_model():
    FastService.calls.clear()
    runtime = start_runtime(FastService)
    try:
        assert submit_one(runtime, 15, detected=[face(60, 60, 10, 10)]) == "queued"
        assert wait_until(lambda: runtime.get_result(15, 0) is not None)
        result = runtime.get_result(15, 0)
        assert result.status == STATUS_INVALID
        assert result.reason == "invalid_face_crop"
        assert FastService.calls == []
    finally:
        runtime.stop()


def test_inference_exception_is_failed_not_thread_crash():
    runtime = start_runtime(FailingService)
    try:
        assert submit_one(runtime, 15) == "queued"
        assert wait_until(lambda: runtime.get_result(15, 0) is not None)
        result = runtime.get_result(15, 0)
        assert result.status == STATUS_FAILED
        assert result.reason == "inference_exception: RuntimeError"
        assert runtime.is_running
    finally:
        runtime.stop()


def test_sampling_and_stale_result_controls():
    runtime = start_runtime(FastService)
    try:
        assert submit_one(runtime, 14) == "not_sampled"
        assert submit_one(runtime, 15) == "queued"
        assert wait_until(lambda: runtime.get_result(15, 0) is not None)
        result = runtime.get_result(15, 0)
        assert result is not None
        assert runtime.is_stale(result, current_frame_sequence=30, max_age_frames=5)
        assert runtime.get_result(15, 0, current_frame_sequence=30, max_age_frames=5) is None
    finally:
        runtime.stop()


def test_security_recognition_receives_original_frame_and_faces():
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    detected = [face()]
    observed = {}

    class Motion:
        def process_frame(self, value):
            return value.copy(), False, None

    class Detection:
        def detect_faces(self, _value):
            return detected

        def draw_faces(self, value, _results):
            return value

    class Recognition:
        def recognize_faces(self, value, faces):
            observed["frame"] = value
            observed["faces"] = faces
            return [{"name": "Unknown", "matched": False, "decision": "unknown_identity"}]

    class Runtime:
        def __init__(self):
            self.submission = None

        def submit_faces(self, value, sequence, faces):
            self.submission = (value, sequence, faces)

    class Events:
        def process_recognition_results(self, **_kwargs):
            pass

    class Integrity:
        def inspect(self, _frame):
            return []

    service = SecurityService.__new__(SecurityService)
    service.motion_service = Motion()
    service.face_service = Detection()
    service.recognition_service = Recognition()
    service.event_service = Events()
    service.integrity_service = Integrity()
    service.face_process_every_n_frames = 3
    service._frame_index = 2
    service._last_faces = []
    service._last_recognition_results = []
    runtime = Runtime()
    service.face_occlusion_runtime = runtime

    service.process_security_frame(frame)

    assert observed["frame"] is frame
    assert observed["faces"] is detected
    assert runtime.submission[0] is frame
    assert runtime.submission[1] == 3
    assert runtime.submission[2] is detected


def test_submission_returns_without_waiting_for_inference():
    BlockingService.started.clear()
    BlockingService.release.clear()
    runtime = start_runtime(BlockingService)
    try:
        started = time.monotonic()
        assert submit_one(runtime, 15) == "queued"
        elapsed = time.monotonic() - started
        assert elapsed < 0.1
        assert BlockingService.started.wait(1.0)
    finally:
        BlockingService.release.set()
        runtime.stop()

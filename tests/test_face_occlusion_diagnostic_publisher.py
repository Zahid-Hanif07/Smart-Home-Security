import json
import time

import httpx

from app.security.face_occlusion_runtime import FaceOcclusionDiagnostic
from app.security.face_occlusion_service import FaceOcclusionResult
from app.services.face_occlusion_diagnostic_publisher import (
    FaceOcclusionDiagnosticPublisher,
)


def wait_until(predicate, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


def diagnostic(*, sequence=1, age=0.0, status="success", reason="segmentation_completed"):
    result = FaceOcclusionResult(
        state="segmentation_available",
        reason="segmentation_completed",
        mode="direct_crop",
        visible_ratio=0.75,
        inference_ms=12.5,
    )
    completed = time.monotonic() - age
    return FaceOcclusionDiagnostic(
        frame_sequence=sequence,
        face_index=0,
        box=(1, 2, 3, 4),
        submitted_at=completed,
        completed_at=completed,
        status=status,
        reason=reason,
        result=result,
    )


def publisher_for(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return FaceOcclusionDiagnosticPublisher(
        lambda: ("session", "00000000-0000-0000-0000-000000000001", time.monotonic() + 30),
        api_base_url="http://test-server",
        backoff_seconds=0.001,
        http_client_factory=lambda: httpx.Client(transport=transport),
        **kwargs,
    )


def test_publishes_only_sanitized_diagnostic_metadata():
    seen = []

    def handler(request):
        seen.append(request)
        body = json.loads(request.content)
        assert request.url.path == "/api/video/face-occlusion"
        assert request.headers["Authorization"].startswith("DeviceSession ")
        assert request.headers["X-Home-ID"] == "00000000-0000-0000-0000-000000000001"
        assert set(body) == {
            "home_id", "face_index", "frame_sequence", "status",
            "visible_ratio", "inference_ms", "result_timestamp", "reason",
        }
        assert body["visible_ratio"] == 0.75
        assert body["inference_ms"] == 12.5
        return httpx.Response(201, request=request)

    publisher = publisher_for(handler)
    publisher.start()
    try:
        assert publisher.submit(diagnostic())
        assert wait_until(lambda: publisher.published_count == 1)
        assert len(seen) == 1
    finally:
        publisher.stop()


def test_unknown_reason_is_collapsed_and_expired_result_is_dropped():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(201, request=request)

    publisher = publisher_for(handler, max_age_seconds=1.0)
    publisher.start()
    try:
        assert publisher.submit(diagnostic(reason="inference_exception: RuntimeError"))
        assert wait_until(lambda: publisher.published_count == 1)
        assert seen[0]["reason"] == "diagnostic_status"
        assert not publisher.submit(diagnostic(sequence=2, age=2.0))
        assert publisher.dropped_expired == 1
    finally:
        publisher.stop()


def test_auth_and_conflict_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(409, request=request)

    publisher = publisher_for(handler, max_retries=2)
    publisher.start()
    try:
        assert publisher.submit(diagnostic())
        assert wait_until(lambda: publisher.last_error is not None)
        assert len(calls) == 1
        assert publisher.retry_count == 0
    finally:
        publisher.stop()


def test_missing_session_does_not_make_a_request():
    calls = []
    transport = httpx.MockTransport(lambda request: calls.append(request))
    publisher = FaceOcclusionDiagnosticPublisher(
        lambda: None,
        api_base_url="http://test-server",
        max_retries=1,
        backoff_seconds=0.001,
        http_client_factory=lambda: httpx.Client(transport=transport),
    )
    publisher.start()
    try:
        assert publisher.submit(diagnostic())
        assert wait_until(lambda: publisher.last_error == "device session unavailable")
        assert calls == []
    finally:
        publisher.stop()


def test_submission_is_non_blocking_and_queue_replaces_pending_item():
    entered = __import__("threading").Event()
    release = __import__("threading").Event()

    def handler(request):
        entered.set()
        release.wait(1.0)
        return httpx.Response(201, request=request)

    publisher = publisher_for(handler)
    publisher.start()
    try:
        started = time.monotonic()
        assert publisher.submit(diagnostic(sequence=1))
        assert time.monotonic() - started < 0.1
        assert entered.wait(1.0)
        assert publisher.submit(diagnostic(sequence=2))
        assert publisher.submit(diagnostic(sequence=3))
        release.set()
        assert wait_until(lambda: publisher.published_count == 2)
        assert publisher.queue_replacements >= 1
    finally:
        release.set()
        publisher.stop()


def test_stop_releases_publisher_thread():
    publisher = publisher_for(lambda request: httpx.Response(201, request=request))
    publisher.start()
    publisher.stop()
    assert publisher._thread is None

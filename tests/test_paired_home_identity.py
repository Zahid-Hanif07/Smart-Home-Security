from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace
import time
from uuid import uuid4

import pytest

from app.security import face_recognition_service as face_recognition_module
from app.security.face_recognition_service import FaceRecognitionService
from app.security.security_event_service import SecurityEventService
from app.security.security_service import SecurityService
from app.streaming.frame_publisher import FramePublisher
from app.ui import camera_worker as camera_worker_module


def _session_payload(home_id: str, token: str = "signed-session") -> dict:
    return {
        "token_type": "DeviceSession",
        "session_token": token,
        "expires_in": 60,
        "home_id": home_id,
    }


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _SessionClient:
    def __init__(self, responses: list[_Response]):
        self.responses = iter(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def test_server_home_overrides_configured_home_and_is_used_for_upload(monkeypatch):
    configured_home = str(uuid4())
    paired_home = str(uuid4())
    publisher = FramePublisher(
        api_base_url="http://localhost:8085",
        home_id=configured_home,
        device_token="test-device-credential",
    )
    client = _SessionClient([_Response(200, _session_payload(paired_home))])

    assert publisher.home_id is None
    assert publisher._ensure_session(client)
    assert publisher.resolved_home_id == paired_home

    uploads = []

    class UploadClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            uploads.append((url, kwargs))
            publisher._running = False
            return _Response(200)

    monkeypatch.setattr(
        "app.streaming.frame_publisher.httpx.Client",
        lambda **_kwargs: UploadClient(),
    )
    publisher._running = True
    publisher._queue.put_nowait(b"jpeg-frame")
    publisher._run()

    assert client.calls[0][0].endswith("/api/devices/session")
    assert len(uploads) == 1
    assert uploads[0][0].endswith("/video/frame")
    assert uploads[0][1]["headers"]["X-Home-ID"] == paired_home
    assert uploads[0][1]["headers"]["X-Home-ID"] != configured_home


@pytest.mark.parametrize("renewed_home", ["same", "changed"])
def test_session_renewal_updates_identity_only_from_valid_response(renewed_home):
    home_a = str(uuid4())
    home_b = home_a if renewed_home == "same" else str(uuid4())
    publisher = FramePublisher(device_token="test-device-credential")
    client = _SessionClient(
        [
            _Response(200, _session_payload(home_a, "initial-session")),
            _Response(200, _session_payload(home_b, "renewed-session")),
        ]
    )

    assert publisher._ensure_session(client)
    assert publisher.resolved_home_id == home_a
    publisher._session_expires_at = time.monotonic() + 1

    assert publisher._ensure_session(client)
    assert publisher._session_token == "renewed-session"
    assert publisher.resolved_home_id == home_b
    assert len(client.calls) == 2


def test_unresolved_face_service_does_not_lookup_configured_home(monkeypatch):
    configured_home = str(uuid4())
    monkeypatch.setenv("SECURITY_HOME_ID", configured_home)
    monkeypatch.setattr(face_recognition_module, "SECURITY_HOME_ID", configured_home)

    class FakeEmbeddingService:
        pass

    class FakeDatabase:
        def load_database(self):
            return {}

    api_calls = []
    monkeypatch.setattr(face_recognition_module, "FaceEmbeddingService", FakeEmbeddingService)
    monkeypatch.setattr(face_recognition_module, "FaceDatabase", FakeDatabase)
    monkeypatch.setattr(
        face_recognition_module,
        "APIClient",
        lambda **kwargs: api_calls.append(kwargs),
    )

    service = FaceRecognitionService(home_id=None, allow_local_database=False)

    assert service.home_id is None
    assert service.registered_people == {}
    assert api_calls == []

    event_calls = []
    events = SecurityEventService(
        api_client=SimpleNamespace(create_security_log=lambda **kwargs: event_calls.append(kwargs)),
        home_id=None,
    )
    assert events.handle_motion_event() is None
    events.shutdown(wait=True)
    assert event_calls == []


def test_face_lookup_replaces_old_home_records_with_server_resolved_home(monkeypatch):
    configured_home = str(uuid4())
    paired_home = str(uuid4())
    monkeypatch.setenv("SECURITY_HOME_ID", configured_home)
    monkeypatch.setattr(face_recognition_module, "SECURITY_HOME_ID", configured_home)

    class FakeEmbeddingService:
        pass

    class FakeDatabase:
        def load_database(self):
            return {}

    lookups = []

    class FakeAPIClient:
        def __init__(self, **_kwargs):
            pass

        def get_home_face_records(self, home_id):
            lookups.append(home_id)
            return [{"member_name": "Paired Home Member", "embedding": [0.25] * 128}]

    monkeypatch.setattr(face_recognition_module, "FaceEmbeddingService", FakeEmbeddingService)
    monkeypatch.setattr(face_recognition_module, "FaceDatabase", FakeDatabase)
    monkeypatch.setattr(face_recognition_module, "APIClient", FakeAPIClient)

    service = FaceRecognitionService(home_id=None, allow_local_database=False)
    service.registered_people = {"Old Home Member": [[0.5] * 128]}
    service.reload_database(home_id=paired_home)

    assert lookups == [paired_home]
    assert service.home_id == paired_home
    assert "Old Home Member" not in service.registered_people
    assert "Paired Home Member" in service.registered_people


def test_security_service_home_change_reloads_faces_and_clears_cached_recognition():
    paired_home = str(uuid4())
    calls = []
    service = SecurityService.__new__(SecurityService)
    service.event_service = SimpleNamespace(set_home_id=calls.append)
    service.recognition_service = SimpleNamespace(
        home_id=None,
        reload_database=lambda home_id: calls.append(("face_lookup", home_id)),
    )
    service.face_process_every_n_frames = 3
    service._frame_index = 7
    service._last_faces = ["old-home-face"]
    service._last_recognition_results = ["old-home-match"]

    service.set_home_id(paired_home)

    assert calls == [paired_home, ("face_lookup", paired_home)]
    assert service.recognition_service.home_id == paired_home
    assert service._last_faces == []
    assert service._last_recognition_results == []
    assert service._frame_index == 2


def test_security_service_keeps_legacy_default_but_accepts_explicit_unresolved_home(monkeypatch):
    configured_home = str(uuid4())
    monkeypatch.setenv("SECURITY_HOME_ID", configured_home)

    class FakeComponent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("app.security.security_service.MotionDetectionService", FakeComponent)
    monkeypatch.setattr("app.security.security_service.FaceDetectionService", FakeComponent)
    monkeypatch.setattr("app.security.security_service.StreamIntegrityService", FakeComponent)
    monkeypatch.setattr("app.security.security_service.FaceRecognitionService", FakeComponent)
    monkeypatch.setattr("app.security.security_service.SecurityEventService", FakeComponent)

    unresolved = SecurityService(home_id=None)
    legacy_default = SecurityService()

    assert unresolved.recognition_service.kwargs == {"home_id": None}
    assert unresolved.event_service.kwargs == {"home_id": None}
    assert legacy_default.recognition_service.kwargs == {}
    assert legacy_default.event_service.kwargs == {}


def test_camera_worker_uses_publisher_home_not_initial_configured_home(monkeypatch):
    configured_home = str(uuid4())
    paired_home = str(uuid4())

    class FakeSecurityService:
        instances = []

        def __init__(self, home_id=None):
            self.home_id = home_id
            self.event_service = SimpleNamespace(on_delivery_status=None)
            self.updated_homes = []
            self.instances.append(self)

        def set_home_id(self, home_id):
            self.home_id = home_id
            self.updated_homes.append(home_id)

    class FakePublisher:
        def __init__(self, **_kwargs):
            self.resolved_home_id = None

        def start(self):
            pass

    monkeypatch.setattr(camera_worker_module, "SecurityService", FakeSecurityService)
    monkeypatch.setattr(camera_worker_module, "FramePublisher", FakePublisher)

    worker = camera_worker_module.CameraWorker(home_id=configured_home)
    security = FakeSecurityService.instances[-1]
    assert security.home_id is None
    worker._sync_resolved_home_id()
    assert security.updated_homes == []

    worker.frame_publisher.resolved_home_id = paired_home
    worker._sync_resolved_home_id()

    assert worker.home_id == paired_home
    assert security.home_id == paired_home
    assert security.updated_homes == [paired_home]


def test_same_home_renewal_does_not_reapply_identity_and_changed_home_does(monkeypatch):
    first_home = str(uuid4())
    changed_home = str(uuid4())

    class FakeSecurityService:
        instances = []

        def __init__(self, home_id=None):
            self.home_id = home_id
            self.event_service = SimpleNamespace(on_delivery_status=None)
            self.updated_homes = []
            self.instances.append(self)

        def set_home_id(self, home_id):
            self.home_id = home_id
            self.updated_homes.append(home_id)

    class FakePublisher:
        def __init__(self, **_kwargs):
            self.resolved_home_id = first_home

        def start(self):
            pass

    monkeypatch.setattr(camera_worker_module, "SecurityService", FakeSecurityService)
    monkeypatch.setattr(camera_worker_module, "FramePublisher", FakePublisher)
    worker = camera_worker_module.CameraWorker()
    security = FakeSecurityService.instances[-1]

    worker._sync_resolved_home_id()
    worker.frame_publisher.resolved_home_id = first_home  # same-home renewal
    worker._sync_resolved_home_id()
    assert security.updated_homes == [first_home]

    worker.frame_publisher.resolved_home_id = changed_home
    worker._sync_resolved_home_id()
    assert security.updated_homes == [first_home, changed_home]


class _DeferredExecutor:
    def __init__(self):
        self.pending = []

    def submit(self, operation):
        future = Future()
        self.pending.append((operation, future))
        return future

    def run_next(self):
        operation, future = self.pending.pop(0)
        future.set_result(operation())

    def shutdown(self, **_kwargs):
        pass


def test_queued_event_keeps_original_home_after_home_switch():
    home_a = str(uuid4())
    home_b = str(uuid4())

    class FakeAPIClient:
        def __init__(self):
            self.home_ids = []

        def create_security_log(self, **kwargs):
            self.home_ids.append(kwargs["home_id"])
            return {"id": str(uuid4())}

    api = FakeAPIClient()
    events = SecurityEventService(api_client=api, home_id=home_a, motion_cooldown=0)
    deferred = _DeferredExecutor()
    events._executor = deferred

    events.handle_motion_event()
    events.set_home_id(home_b)
    deferred.run_next()
    events.handle_motion_event()
    deferred.run_next()

    assert api.home_ids == [home_a, home_b]


@pytest.mark.parametrize(
    "status_code,payload",
    [
        (200, {**_session_payload(str(uuid4())), "home_id": "not-a-uuid"}),
        (200, {key: value for key, value in _session_payload(str(uuid4())).items() if key != "home_id"}),
        (401, None),
    ],
)
@pytest.mark.parametrize("prior_home", [None, str(uuid4())])
def test_invalid_or_failed_session_does_not_upload_and_retains_last_identity(
    monkeypatch, status_code, payload, prior_home
):
    publisher = FramePublisher(
        api_base_url="http://localhost:8085",
        device_token="test-device-credential",
    )
    publisher._resolved_home_id = prior_home
    publisher._session_token = "expired-session"
    publisher._session_expires_at = time.monotonic() + 1

    class OneRequestClient:
        def __init__(self, **_kwargs):
            self.uploads = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **_kwargs):
            if url.endswith("/api/devices/session"):
                publisher._running = False
                return _Response(status_code, payload)
            self.uploads.append(url)
            return _Response(200)

    client = OneRequestClient()
    monkeypatch.setattr("app.streaming.frame_publisher.httpx.Client", lambda **kwargs: client)
    publisher._running = True
    publisher._queue.put_nowait(b"jpeg-frame")

    publisher._run()

    assert client.uploads == []
    assert publisher._session_token is None
    assert publisher.resolved_home_id == prior_home

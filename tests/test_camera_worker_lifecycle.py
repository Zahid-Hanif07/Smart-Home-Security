import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui import camera_worker as camera_worker_module


class FakeCapture:
    def __init__(self, opened=True, reads=None):
        self.opened = opened
        self.reads = list(reads or [])
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if self.reads:
            return self.reads.pop(0)
        return False, None

    def release(self):
        self.released = True


class FakeCleanup:
    def __init__(self):
        self.start_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1


class FakeSecurityService:
    def __init__(self, home_id=None, *, process_error=None, worker=None):
        self.event_service = SimpleNamespace(
            on_delivery_status=None,
            shutdown=lambda **_kwargs: None,
            handle_system_event=lambda _item: None,
        )
        self.integrity_service = SimpleNamespace(
            inspect=lambda *_args, **_kwargs: [],
        )
        self.recognition_service = SimpleNamespace(database_error=None)
        self.frame_sequence = 0
        self.process_error = process_error
        self.worker = worker

    def set_face_occlusion_runtime(self, _runtime):
        pass

    def reload_face_database(self):
        pass

    def process_security_frame(self, frame):
        if self.process_error is not None:
            raise self.process_error
        return frame, False, False, 0, []


class FakeFramePublisher(FakeCleanup):
    def __init__(self, **_kwargs):
        super().__init__()
        self.resolved_home_id = None
        self.device_token = None
        self.last_error = None
        self.published = []

    def publish(self, jpeg):
        self.published.append(jpeg)


class FakeRuntime(FakeCleanup):
    max_result_age_frames = 30
    max_result_age_seconds = 2.0
    latest_result = None

    def drain_results(self):
        return []


class FakeDiagnosticPublisher(FakeCleanup):
    def __init__(self, **_kwargs):
        super().__init__()
        self.submitted = []

    def submit(self, diagnostic):
        self.submitted.append(diagnostic)


@pytest.fixture
def worker_factory(monkeypatch):
    captures = []
    frame_publishers = []
    runtimes = []
    diagnostic_publishers = []
    security_services = []

    def video_capture(_index):
        capture = make.capture
        captures.append(capture)
        return capture

    def frame_publisher(**kwargs):
        publisher = FakeFramePublisher(**kwargs)
        frame_publishers.append(publisher)
        return publisher

    def runtime(**_kwargs):
        instance = FakeRuntime()
        runtimes.append(instance)
        return instance

    def diagnostic_publisher(**kwargs):
        publisher = FakeDiagnosticPublisher(**kwargs)
        diagnostic_publishers.append(publisher)
        return publisher

    def security_service(**kwargs):
        instance = FakeSecurityService(**kwargs)
        security_services.append(instance)
        return instance

    make = None
    monkeypatch.setattr(camera_worker_module.cv2, "VideoCapture", video_capture)
    monkeypatch.setattr(camera_worker_module, "FramePublisher", frame_publisher)
    monkeypatch.setattr(camera_worker_module, "FaceOcclusionRuntime", runtime)
    monkeypatch.setattr(
        camera_worker_module,
        "FaceOcclusionDiagnosticPublisher",
        diagnostic_publisher,
    )
    monkeypatch.setattr(camera_worker_module, "SecurityService", security_service)
    monkeypatch.setattr(
        camera_worker_module,
        "get_frame_manager",
        lambda: SimpleNamespace(
            update_frame=lambda _frame: None,
            get_latest_jpeg=lambda: b"jpeg",
        ),
    )

    def make(*, opened=True, reads=None, process_error=None):
        make.capture = FakeCapture(opened=opened, reads=reads)
        worker = camera_worker_module.CameraWorker()
        if process_error is not None:
            security_services[-1].process_error = process_error
        return worker, make.capture, frame_publishers[-1], runtimes[-1], diagnostic_publishers[-1]

    make.capture = FakeCapture()
    make.captures = captures
    make.frame_publishers = frame_publishers
    make.runtimes = runtimes
    make.diagnostic_publishers = diagnostic_publishers
    make.security_services = security_services
    worker_factory.make = make
    return make


def test_successful_startup_reads_frame_and_stops_all_resources(worker_factory):
    worker, capture, frame_publisher, runtime, diagnostic_publisher = worker_factory(
        opened=True,
        reads=[(True, object()), (False, None)],
    )

    worker.run()

    assert capture.released
    assert frame_publisher.start_calls == 1
    assert frame_publisher.stop_calls == 1
    assert runtime.start_calls == 1
    assert runtime.stop_calls == 1
    assert diagnostic_publisher.start_calls == 1
    assert diagnostic_publisher.stop_calls == 1


def test_camera_open_failure_reports_and_cleans_up(worker_factory):
    worker, capture, frame_publisher, runtime, diagnostic_publisher = worker_factory(
        opened=False
    )
    errors = []
    worker.error_occurred.connect(errors.append)

    worker.run()

    assert errors and "Unable to access camera" in errors[0]
    assert capture.released
    assert frame_publisher.stop_calls == 1
    assert runtime.stop_calls == 0
    assert diagnostic_publisher.stop_calls == 0


def test_camera_read_failure_releases_capture_and_faceocc_resources(worker_factory):
    worker, capture, frame_publisher, runtime, diagnostic_publisher = worker_factory(
        opened=True,
        reads=[(False, None)],
    )

    worker.run()

    assert capture.released
    assert frame_publisher.stop_calls == 1
    assert runtime.stop_calls == 1
    assert diagnostic_publisher.stop_calls == 1


def test_processing_exception_still_releases_capture_and_publishers(worker_factory):
    worker, capture, frame_publisher, runtime, diagnostic_publisher = worker_factory(
        opened=True,
        reads=[(True, object())],
        process_error=RuntimeError("test processing failure"),
    )
    errors = []
    worker.error_occurred.connect(errors.append)

    worker.run()

    assert errors and "Unexpected camera error" in errors[0]
    assert capture.released
    assert frame_publisher.stop_calls == 1
    assert runtime.stop_calls == 1
    assert diagnostic_publisher.stop_calls == 1


def test_repeated_sequential_workers_release_independent_resources(worker_factory):
    first = worker_factory(opened=True, reads=[(False, None)])
    first[0].run()

    second = worker_factory(opened=True, reads=[(False, None)])
    second[0].run()

    for worker_tuple in (first, second):
        assert worker_tuple[1].released
        assert worker_tuple[2].stop_calls == 1
        assert worker_tuple[3].stop_calls == 1
        assert worker_tuple[4].stop_calls == 1

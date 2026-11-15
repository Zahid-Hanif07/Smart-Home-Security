"""Focused frame-session authentication and publisher renewal tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time
from uuid import UUID, uuid4

os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import cv2
import jwt
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.repositories.pairing_repository import pairing_repository
from app.security.device_credential import parse_token
from app.security.device_session_token import (
    DEVICE_SESSION_AUDIENCE,
    DEVICE_SESSION_ISSUER,
    create_device_session_token,
)
from app.services.backend_store import backend_store
from app.streaming.frame_manager import get_frame_manager
from app.streaming.frame_publisher import FramePublisher

_USER_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"
_SESSION_SECRET = "test-device-session-key-for-video-route-tests-32-bytes"
client = TestClient(app, raise_server_exceptions=True)


def _jwt(user_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "id": user_id,
            "email": "video-session-test@example.local",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        _USER_SECRET,
        algorithm="HS256",
    )


def _jpeg() -> bytes:
    ok, buf = cv2.imencode(".jpg", np.zeros((32, 32, 3), dtype=np.uint8))
    assert ok
    return buf.tobytes()


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    backend_store.clear()
    pairing_repository.clear()
    fm = get_frame_manager()
    fm._latest_jpeg = None
    fm._home_id = None
    fm._last_update_time = 0.0
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", _SESSION_SECRET)
    yield
    backend_store.clear()
    pairing_repository.clear()
    fm._latest_jpeg = None
    fm._home_id = None
    fm._last_update_time = 0.0


def _publisher() -> tuple[str, str, UUID, UUID, str, str]:
    user_id = str(uuid4())
    user_token = _jwt(user_id)
    user_headers = {"Authorization": f"Bearer {user_token}"}
    response = client.post("/api/homes", json={"name": "Session Home"}, headers=user_headers)
    assert response.status_code == 201, response.text
    home_id = response.json()["id"]
    response = client.post(f"/api/homes/{home_id}/pairing-codes", headers=user_headers)
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/pairing/claim",
        json={
            "code": response.json()["code"],
            "device_name": "Session Camera",
            "device_type": "desktop_camera",
            "device_identifier": str(uuid4()),
        },
    )
    assert response.status_code == 200, response.text
    device_token = response.json()["device_token"]
    response = client.post(
        "/api/devices/session",
        headers={"Authorization": f"DeviceToken {device_token}"},
    )
    assert response.status_code == 200, response.text
    return (
        user_id,
        user_token,
        UUID(home_id),
        parse_token(device_token)[0],
        device_token,
        response.json()["session_token"],
    )


def _frame(session_token: str, home_id: UUID):
    return client.post(
        "/video/frame",
        content=_jpeg(),
        headers={
            "Authorization": f"DeviceSession {session_token}",
            "Content-Type": "image/jpeg",
            "X-Home-ID": str(home_id),
        },
    )


def test_valid_device_session_can_upload_frame():
    _, _, home_id, _, _, session_token = _publisher()

    response = _frame(session_token, home_id)

    assert response.status_code == 200, response.text
    assert get_frame_manager().get_home_id() == str(home_id)


def test_frame_upload_does_not_verify_device_bcrypt_credential(monkeypatch):
    _, _, home_id, _, _, session_token = _publisher()

    def fail_if_bcrypt_is_called(*_args, **_kwargs):
        raise AssertionError("bcrypt verification must not run for a frame upload")

    from app.security import device_credential
    monkeypatch.setattr(device_credential, "verify_token_secret", fail_if_bcrypt_is_called)

    response = _frame(session_token, home_id)

    assert response.status_code == 200, response.text


def test_invalid_signature_and_expired_session_are_rejected():
    _, _, home_id, device_id, _, session_token = _publisher()
    valid_claims = jwt.decode(session_token, options={"verify_signature": False})
    bad_signature = jwt.encode(valid_claims, "different-test-key-that-is-not-the-session-key", algorithm="HS256")
    expired_session = create_device_session_token(
        device_id=device_id,
        home_id=home_id,
        now=datetime.now(timezone.utc) - timedelta(seconds=61),
    )

    assert _frame(bad_signature, home_id).status_code == 401
    assert _frame(expired_session, home_id).status_code == 401


def test_session_home_header_and_device_claim_mismatches_are_rejected():
    _, _, home_id, device_id, _, session_token = _publisher()
    other_home_id = uuid4()
    now = int(time.time())
    mismatched_device = jwt.encode(
        {
            "iss": DEVICE_SESSION_ISSUER,
            "aud": DEVICE_SESSION_AUDIENCE,
            "sub": str(device_id),
            "device_id": str(uuid4()),
            "home_id": str(home_id),
            "iat": now,
            "exp": now + 60,
            "jti": "mismatched-device-test",
        },
        _SESSION_SECRET,
        algorithm="HS256",
    )

    assert _frame(session_token, other_home_id).status_code == 401
    assert _frame(mismatched_device, home_id).status_code == 401


def test_revoked_device_cannot_publish_with_an_unexpired_session():
    _, user_token, home_id, device_id, _, session_token = _publisher()
    assert _frame(session_token, home_id).status_code == 200
    count_before_revoke = get_frame_manager().get_status()["frame_count"]

    revoke_response = client.post(
        f"/api/devices/{device_id}/revoke",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert revoke_response.status_code == 204
    upload_response = _frame(session_token, home_id)

    assert upload_response.status_code == 401
    assert get_frame_manager().get_status()["frame_count"] == count_before_revoke


def test_revoked_device_cannot_renew_session():
    _, user_token, _, device_id, device_token, _ = _publisher()
    revoke_response = client.post(
        f"/api/devices/{device_id}/revoke",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert revoke_response.status_code == 204

    renewal_response = client.post(
        "/api/devices/session",
        headers={"Authorization": f"DeviceToken {device_token}"},
    )

    assert renewal_response.status_code == 401


def test_homeowner_bearer_still_views_status_and_mjpeg_stream(monkeypatch):
    _, user_token, home_id, _, _, session_token = _publisher()
    assert _frame(session_token, home_id).status_code == 200
    homeowner_headers = {"Authorization": f"Bearer {user_token}"}

    async def one_frame(**_kwargs):
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe\r\n"

    from app.api.routes import video as video_routes
    monkeypatch.setattr(video_routes, "generate_mjpeg_stream", one_frame)

    status_response = client.get(f"/video/status?home_id={home_id}", headers=homeowner_headers)
    stream_response = client.get(
        f"/video/stream?home_id={home_id}",
        headers=homeowner_headers,
    )
    assert status_response.status_code == 200
    assert stream_response.status_code == 200
    assert "multipart/x-mixed-replace" in stream_response.headers["content-type"]


def test_failed_session_renewal_discards_cached_session_without_fallback():
    class Response:
        status_code = 401

    class FakeClient:
        def __init__(self):
            self.calls = []

        def post(self, url, headers):
            self.calls.append((url, headers))
            return Response()

    publisher = FramePublisher(
        api_base_url="http://localhost:8085",
        home_id=str(uuid4()),
        device_token="dvc_test-secret-credential",
    )
    publisher._session_token = "expired-or-expiring-session"
    publisher._session_expires_at = time.monotonic() + 1
    client_stub = FakeClient()

    renewed = publisher._ensure_session(client_stub)

    assert renewed is False
    assert publisher._session_token is None
    assert publisher.last_error == "device session endpoint returned HTTP 401"
    assert client_stub.calls == [
        (
            "http://localhost:8085/api/devices/session",
            {"Authorization": "DeviceToken dvc_test-secret-credential"},
        )
    ]


def test_expiring_session_is_renewed_before_frame_upload():
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "session_token": "new-signed-session",
                "token_type": "DeviceSession",
                "expires_in": 60,
                "home_id": str(resolved_home_id),
            }

    class FakeClient:
        def __init__(self):
            self.calls = []

        def post(self, url, headers):
            self.calls.append((url, headers))
            return Response()

    resolved_home_id = uuid4()
    publisher = FramePublisher(
        api_base_url="http://localhost:8085",
        home_id=str(uuid4()),
        device_token="dvc_test-secret-credential",
    )
    publisher._session_token = "expiring-session"
    publisher._session_expires_at = time.monotonic() + 5
    client_stub = FakeClient()

    assert publisher._ensure_session(client_stub) is True
    assert publisher._session_token == "new-signed-session"
    assert publisher.home_id == str(resolved_home_id)
    assert publisher._session_expires_at > time.monotonic() + 50
    assert len(client_stub.calls) == 1


def test_frame_publisher_upload_uses_home_resolved_by_session_exchange(monkeypatch):
    resolved_home_id = uuid4()
    upload_calls = []
    publisher = FramePublisher(
        api_base_url="http://localhost:8085",
        home_id=str(uuid4()),
        device_token="dvc_test-secret-credential",
    )

    class Response:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            if url.endswith("/api/devices/session"):
                return Response(200, {
                    "session_token": "server-issued-session",
                    "token_type": "DeviceSession",
                    "expires_in": 60,
                    "home_id": str(resolved_home_id),
                })
            upload_calls.append((url, kwargs))
            publisher._running = False
            return Response(200)

    monkeypatch.setattr("app.streaming.frame_publisher.httpx.Client", lambda **_kwargs: FakeClient())
    publisher._running = True
    publisher._queue.put_nowait(b"jpeg-frame")

    publisher._run()

    assert len(upload_calls) == 1
    url, request = upload_calls[0]
    assert url == "http://localhost:8085/video/frame"
    assert request["headers"]["Authorization"] == "DeviceSession server-issued-session"
    assert request["headers"]["X-Home-ID"] == str(resolved_home_id)


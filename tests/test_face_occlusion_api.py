"""Isolated tests for the home-scoped FaceOcc diagnostic API."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.repositories.pairing_repository import pairing_repository
from app.services.backend_store import backend_store
from app.services.face_occlusion_diagnostic_store import face_occlusion_diagnostic_store


client = TestClient(app, raise_server_exceptions=True)
_USER_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"
_SESSION_SECRET = "test-faceocc-device-session-key-at-least-32-bytes"


def owner_token(user_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "id": user_id,
            "email": "faceocc-test@example.local",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        _USER_SECRET,
        algorithm="HS256",
    )


def paired_device() -> tuple[str, str, str, str]:
    user_id = str(uuid4())
    token = owner_token(user_id)
    response = client.post(
        "/api/homes",
        json={"name": "FaceOcc Test Home"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    home_id = response.json()["id"]
    response = client.post(
        f"/api/homes/{home_id}/pairing-codes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/pairing/claim",
        json={
            "code": response.json()["code"],
            "device_name": "FaceOcc Test Camera",
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
    return user_id, token, home_id, response.json()["session_token"]


def diagnostic(home_id: str, *, timestamp=None, **overrides):
    value = {
        "home_id": home_id,
        "face_index": 0,
        "frame_sequence": 15,
        "status": "success",
        "visible_ratio": 0.75,
        "inference_ms": 12.5,
        "result_timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "reason": "segmentation_completed",
    }
    value.update(overrides)
    return value


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    backend_store.clear()
    pairing_repository.clear()
    face_occlusion_diagnostic_store.clear()
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", _SESSION_SECRET)
    yield
    face_occlusion_diagnostic_store.clear()
    backend_store.clear()
    pairing_repository.clear()


def publish_headers(session_token: str, home_id: str) -> dict[str, str]:
    return {
        "Authorization": f"DeviceSession {session_token}",
        "X-Home-ID": home_id,
    }


def test_valid_device_publish_and_authorized_retrieval():
    user_id, user_jwt, home_id, session = paired_device()
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id),
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["home_id"] == home_id
    assert body["face_index"] == 0
    assert body["freshness"] == "fresh"
    assert "logits" not in body
    assert "binary_mask" not in body
    assert "probability_map" not in body

    response = client.get(
        f"/api/video/face-occlusion/status?home_id={home_id}",
        headers={"Authorization": f"Bearer {user_jwt}"},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_publish_requires_device_session_and_get_requires_bearer():
    _, _, home_id, _ = paired_device()
    assert client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id),
        headers={"X-Home-ID": home_id},
    ).status_code == 401
    assert client.get(
        f"/api/video/face-occlusion/status?home_id={home_id}"
    ).status_code == 401


def test_device_cannot_publish_for_another_home():
    _, owner_jwt, home_id, session = paired_device()
    response = client.post(
        "/api/homes",
        json={"name": "Other Home"},
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    other_home_id = response.json()["id"]
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(other_home_id),
        headers=publish_headers(session, other_home_id),
    )
    assert response.status_code == 401


def test_user_cannot_retrieve_another_users_home():
    _, _, home_id, _ = paired_device()
    other_user = owner_token(str(uuid4()))
    response = client.get(
        f"/api/video/face-occlusion/status?home_id={home_id}",
        headers={"Authorization": f"Bearer {other_user}"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "unsupported"},
        {"visible_ratio": 1.1},
        {"inference_ms": -1},
        {"visible_ratio": "NaN"},
        {"inference_ms": "Infinity"},
        {"result_timestamp": "2026-01-01T00:00:00"},
    ],
)
def test_invalid_diagnostic_values_are_rejected(overrides):
    _, _, home_id, session = paired_device()
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id, **overrides),
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "reason",
    ["", "segmentation_completed", "no_face_detected", "diagnostic_status"],
)
def test_reason_values_are_accepted(reason):
    _, _, home_id, session = paired_device()
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id, reason=reason),
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 201, response.text
    assert response.json()["reason"] == reason


def test_missing_reason_uses_safe_default():
    _, _, home_id, session = paired_device()
    payload = diagnostic(home_id)
    payload.pop("reason")
    response = client.post(
        "/api/video/face-occlusion",
        json=payload,
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 201, response.text
    assert response.json()["reason"] == ""


@pytest.mark.parametrize("reason", ["private backend detail", "inference_exception: RuntimeError"])
def test_unrecognized_reason_is_rejected(reason):
    _, _, home_id, session = paired_device()
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id, reason=reason),
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 422


def test_oversized_reason_is_rejected():
    _, _, home_id, session = paired_device()
    response = client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id, reason="x" * 121),
        headers=publish_headers(session, home_id),
    )
    assert response.status_code == 422


def test_older_result_is_rejected_and_expired_result_is_stale():
    _, owner_jwt, home_id, session = paired_device()
    current_time = datetime.now(timezone.utc)
    first_time = current_time - timedelta(seconds=20)
    first = client.post(
        "/video/face-occlusion",
        json=diagnostic(home_id, timestamp=first_time.isoformat(), frame_sequence=30),
        headers=publish_headers(session, home_id),
    )
    assert first.status_code == 201
    older = client.post(
        "/video/face-occlusion",
        json=diagnostic(
            home_id,
            timestamp=(first_time - timedelta(seconds=1)).isoformat(),
            frame_sequence=15,
        ),
        headers=publish_headers(session, home_id),
    )
    assert older.status_code == 409

    expired = client.post(
        "/video/face-occlusion",
        json=diagnostic(
            home_id,
            timestamp=(current_time - timedelta(seconds=10)).isoformat(),
            frame_sequence=45,
        ),
        headers=publish_headers(session, home_id),
    )
    assert expired.status_code == 201
    response = client.get(
        f"/video/face-occlusion/status?home_id={home_id}",
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["freshness"] == "stale"


def test_store_is_in_memory_and_clear_removes_results():
    _, owner_jwt, home_id, session = paired_device()
    assert client.post(
        "/api/video/face-occlusion",
        json=diagnostic(home_id),
        headers=publish_headers(session, home_id),
    ).status_code == 201
    face_occlusion_diagnostic_store.clear()
    response = client.get(
        f"/api/video/face-occlusion/status?home_id={home_id}",
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []

"""Focused isolated tests for device-session exchange and renewal."""
from __future__ import annotations

import os
import secrets
import time
from uuid import UUID, uuid4

os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.repositories.pairing_repository import pairing_repository
from app.security.device_credential import TOKEN_PREFIX, parse_token
from app.security.device_session_token import (
    DEVICE_SESSION_AUDIENCE,
    DEVICE_SESSION_ISSUER,
    DEVICE_SESSION_MAX_LIFETIME_SECONDS,
    validate_device_session_token,
)
from app.services.backend_store import backend_store

_USER_JWT_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"
_SESSION_SECRET = "test-device-session-key-for-exchange-tests-at-least-32-bytes"
client = TestClient(app, raise_server_exceptions=True)


def _owner_token(user_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "id": user_id,
            "email": "device-session-test@example.local",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        _USER_JWT_SECRET,
        algorithm="HS256",
    )


def _paired_device() -> tuple[str, str, str, str]:
    user_id = str(uuid4())
    owner_jwt = _owner_token(user_id)
    response = client.post(
        "/api/homes",
        json={"name": "Device Session Test Home"},
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    assert response.status_code == 201, response.text
    home_id = response.json()["id"]
    response = client.post(
        f"/api/homes/{home_id}/pairing-codes",
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/pairing/claim",
        json={
            "code": response.json()["code"],
            "device_name": "Session Test Camera",
            "device_type": "desktop_camera",
            "device_identifier": str(uuid4()),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return user_id, owner_jwt, home_id, body["device_token"]


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    backend_store.clear()
    pairing_repository.clear()
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", _SESSION_SECRET)
    yield
    backend_store.clear()
    pairing_repository.clear()


def _exchange(device_token: str, **kwargs):
    return client.post(
        "/api/devices/session",
        headers={"Authorization": f"DeviceToken {device_token}"},
        **kwargs,
    )


def test_exchange_issues_short_lived_device_and_home_bound_session():
    _, _, home_id, device_token = _paired_device()
    device_id, _ = parse_token(device_token)

    response = _exchange(device_token)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"session_token", "token_type", "expires_in", "home_id"}
    assert body["token_type"] == "DeviceSession"
    assert body["expires_in"] == DEVICE_SESSION_MAX_LIFETIME_SECONDS
    assert body["home_id"] == home_id
    claims = validate_device_session_token(
        body["session_token"],
        expected_device_id=device_id,
        expected_home_id=UUID(home_id),
    )
    assert claims["device_id"] == str(device_id)
    assert claims["home_id"] == home_id
    assert claims["iss"] == DEVICE_SESSION_ISSUER
    assert claims["aud"] == DEVICE_SESSION_AUDIENCE


def test_renewal_revalidates_device_credential_and_returns_fresh_session():
    _, _, home_id, device_token = _paired_device()
    device_id, _ = parse_token(device_token)

    first = _exchange(device_token)
    renewed = _exchange(device_token)

    assert first.status_code == renewed.status_code == 200
    assert first.json()["session_token"] != renewed.json()["session_token"]
    validate_device_session_token(
        renewed.json()["session_token"],
        expected_device_id=device_id,
        expected_home_id=UUID(home_id),
    )


def test_invalid_credential_is_rejected():
    _, _, _, device_token = _paired_device()
    device_id, _ = parse_token(device_token)
    invalid_token = f"{TOKEN_PREFIX}_{device_id.hex}_{secrets.token_hex(32)}"

    response = _exchange(invalid_token)

    assert response.status_code == 401


def test_revoked_device_cannot_exchange_or_renew_session():
    _, owner_jwt, _, device_token = _paired_device()
    device_id, _ = parse_token(device_token)
    revoked = client.post(
        f"/api/devices/{device_id}/revoke",
        headers={"Authorization": f"Bearer {owner_jwt}"},
    )
    assert revoked.status_code == 204

    response = _exchange(device_token)

    assert response.status_code == 401


def test_client_supplied_home_id_does_not_override_stored_home():
    _, _, home_id, device_token = _paired_device()
    device_id, _ = parse_token(device_token)
    other_home_id = str(uuid4())

    response = _exchange(device_token, json={"home_id": other_home_id})

    assert response.status_code == 200, response.text
    claims = validate_device_session_token(
        response.json()["session_token"],
        expected_device_id=device_id,
        expected_home_id=UUID(home_id),
    )
    assert claims["home_id"] != other_home_id


def test_missing_session_signing_configuration_fails_closed(monkeypatch):
    _, _, _, device_token = _paired_device()
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", "")

    response = _exchange(device_token)

    assert response.status_code == 503
    assert response.json()["detail"] == "Device session signing is not configured."


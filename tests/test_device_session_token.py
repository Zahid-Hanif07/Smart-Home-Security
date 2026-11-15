"""Focused tests for the Phase 3B.1 device-session JWT primitive."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.config.backend_settings import settings
from app.security.device_session_token import (
    DEVICE_SESSION_ALGORITHM,
    DEVICE_SESSION_AUDIENCE,
    DEVICE_SESSION_ISSUER,
    DEVICE_SESSION_MAX_LIFETIME_SECONDS,
    create_device_session_token,
    validate_device_session_token,
)

_TEST_SIGNING_SECRET = "test-only-device-session-key-with-at-least-48-bytes"


@pytest.fixture(autouse=True)
def configured_session_secret(monkeypatch):
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", _TEST_SIGNING_SECRET)


def _ids():
    return uuid4(), uuid4()


def _make_token(*, device_id, home_id, overrides=None, secret=_TEST_SIGNING_SECRET, algorithm="HS256"):
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": DEVICE_SESSION_ISSUER,
        "aud": DEVICE_SESSION_AUDIENCE,
        "sub": str(device_id),
        "device_id": str(device_id),
        "home_id": str(home_id),
        "iat": now,
        "exp": now + DEVICE_SESSION_MAX_LIFETIME_SECONDS,
        "jti": "test-session-id",
    }
    claims.update(overrides or {})
    return jwt.encode(claims, secret, algorithm=algorithm)


def test_valid_token_binds_device_and_home():
    device_id, home_id = _ids()

    token = create_device_session_token(device_id=device_id, home_id=home_id)
    claims = validate_device_session_token(
        token,
        expected_device_id=device_id,
        expected_home_id=home_id,
    )

    assert claims["sub"] == str(device_id)
    assert claims["device_id"] == str(device_id)
    assert claims["home_id"] == str(home_id)
    assert claims["exp"] - claims["iat"] <= DEVICE_SESSION_MAX_LIFETIME_SECONDS


def test_invalid_signature_is_rejected():
    device_id, home_id = _ids()
    token = _make_token(
        device_id=device_id,
        home_id=home_id,
        secret="different-test-device-session-key-with-at-least-48-bytes",
    )

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


def test_wrong_algorithm_is_rejected():
    device_id, home_id = _ids()
    token = _make_token(device_id=device_id, home_id=home_id, algorithm="HS384")

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


@pytest.mark.parametrize("claim,value", [("iss", "another-issuer"), ("aud", "another-audience")])
def test_wrong_issuer_or_audience_is_rejected(claim, value):
    device_id, home_id = _ids()
    token = _make_token(device_id=device_id, home_id=home_id, overrides={claim: value})

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


def test_expired_token_is_rejected():
    device_id, home_id = _ids()
    token = _make_token(
        device_id=device_id,
        home_id=home_id,
        overrides={"iat": int(datetime.now(timezone.utc).timestamp()) - 120,
                   "exp": int(datetime.now(timezone.utc).timestamp()) - 60},
    )

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


def test_missing_required_claim_is_rejected():
    device_id, home_id = _ids()
    claims = {
        "iss": DEVICE_SESSION_ISSUER,
        "aud": DEVICE_SESSION_AUDIENCE,
        "sub": str(device_id),
        "device_id": str(device_id),
        "home_id": str(home_id),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=30)).timestamp()),
        # jti intentionally omitted
    }
    token = jwt.encode(claims, _TEST_SIGNING_SECRET, algorithm=DEVICE_SESSION_ALGORITHM)

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


@pytest.mark.parametrize("mismatch", ["device", "subject", "home"])
def test_device_or_home_claim_mismatch_is_rejected(mismatch):
    device_id, home_id = _ids()
    other_id = uuid4()
    claims = {"device_id": str(other_id)} if mismatch == "device" else {}
    if mismatch == "subject":
        claims["sub"] = str(other_id)
    if mismatch == "home":
        claims["home_id"] = str(other_id)
    token = _make_token(device_id=device_id, home_id=home_id, overrides=claims)

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


def test_token_lifetime_cannot_exceed_60_seconds():
    device_id, home_id = _ids()

    with pytest.raises(ValueError, match="between 1 and 60 seconds"):
        create_device_session_token(device_id=device_id, home_id=home_id, lifetime_seconds=61)


def test_validator_rejects_token_with_lifetime_over_60_seconds():
    device_id, home_id = _ids()
    now = int(datetime.now(timezone.utc).timestamp())
    token = _make_token(
        device_id=device_id,
        home_id=home_id,
        overrides={"iat": now, "exp": now + DEVICE_SESSION_MAX_LIFETIME_SECONDS + 1},
    )

    with pytest.raises(ValueError, match="Invalid device session token"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


def test_missing_signing_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", "")
    device_id, home_id = _ids()

    with pytest.raises(ValueError, match="DEVICE_SESSION_SIGNING_SECRET"):
        create_device_session_token(device_id=device_id, home_id=home_id)


def test_validator_reports_missing_signing_secret(monkeypatch):
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", "")
    device_id, home_id = _ids()
    token = _make_token(device_id=device_id, home_id=home_id)

    with pytest.raises(ValueError, match="DEVICE_SESSION_SIGNING_SECRET"):
        validate_device_session_token(token, expected_device_id=device_id, expected_home_id=home_id)


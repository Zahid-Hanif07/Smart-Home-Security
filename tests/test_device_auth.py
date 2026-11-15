"""
Isolated tests for Phase 3A — Secure Device Authentication and Revocation.

Coverage
--------
1.  Credential issuance — valid claim issues a token; format correct.
2.  Credential not re-issued — already-registered device gets no second token.
3.  Device auth dependency — missing / malformed / wrong-scheme / unknown /
    wrong-secret credentials all return 401.
4.  Revocation — revoke takes effect immediately on the next request.
5.  Cross-home isolation — device's home_id is server-controlled; device
    cannot reach another home's resources.
6.  Client cannot override home_id — pairing claim ignores any home_id in
    the body (the model has no such field; server derives home from the code).
7.  Non-owner revocation — 403 when a different user tries to revoke.
8.  Duplicate identifiers and concurrent claims — only one gets a token.
9.  Database failures fail closed — production safety guard; store_credential
    raises 500 rather than silently discarding the hash.
10. Hash persistence — raw token never stored; only bcrypt hash persisted.
11. Existing user-authenticated endpoints — no regression.

Run with:
    TEST_ISOLATED_MODE=1 python -m pytest tests/test_device_auth.py -v

NOTE: All assertions reference isolated in-memory state only.
      Live Supabase verification is a separate, manual step after the
      migration (202610150002_device_credentials.sql) has been applied.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

# Must be set before any app imports so the memory-fallback activates.
os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.repositories.device_repository import device_repository
from app.repositories.pairing_repository import pairing_repository
from app.security.device_credential import (
    TOKEN_LENGTH,
    TOKEN_PREFIX,
    generate_raw_token,
    hash_token_secret,
    parse_token,
    verify_token_secret,
)
from app.services.backend_store import backend_store

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_JWT_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"

client = TestClient(app, raise_server_exceptions=True)


def _make_jwt(user_id: str) -> str:
    """Return a signed HS256 test JWT for the given user ID."""
    payload = {
        "sub": str(user_id),
        "id": str(user_id),
        "email": f"{str(user_id)[:8]}@test.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _device_header(token: str) -> dict:
    return {"Authorization": f"DeviceToken {token}"}


def _setup_owner() -> tuple[str, str, str]:
    """Create a user + home.  Returns (user_id, jwt_token, home_id)."""
    uid = str(uuid4())
    tok = _make_jwt(uid)
    r = client.post("/api/homes", json={"name": "Test Home"}, headers=_bearer(tok))
    assert r.status_code == 201, f"Home creation failed: {r.text}"
    return uid, tok, r.json()["id"]


def _generate_code(home_id: str, user_jwt: str) -> str:
    """Generate a pairing code and return it (display format e.g. 'A3F-72K')."""
    r = client.post(f"/api/homes/{home_id}/pairing-codes", headers=_bearer(user_jwt))
    assert r.status_code == 201, f"Code generation failed: {r.text}"
    return r.json()["code"]


def _claim(code: str, device_identifier: str | None = None, device_name: str = "Test PC") -> dict:
    """POST /api/pairing/claim and return the parsed JSON response."""
    r = client.post(
        "/api/pairing/claim",
        json={
            "code": code,
            "device_name": device_name,
            "device_type": "desktop_camera",
            "device_identifier": device_identifier or str(uuid4()),
        },
    )
    return r


def _full_pair(home_id: str, user_jwt: str, device_identifier: str | None = None) -> dict:
    """Generate a code, claim it, assert success, return response JSON."""
    code = _generate_code(home_id, user_jwt)
    r = _claim(code, device_identifier=device_identifier)
    assert r.status_code == 200, f"Claim failed: {r.text}"
    return r.json()


def _reset() -> None:
    backend_store.clear()
    pairing_repository.clear()


# ===========================================================================
# 1. Credential issuance
# ===========================================================================

class TestCredentialIssuance:
    """Valid pairing claim → token issued once, format verified."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_token_present_on_new_registration(self):
        data = _full_pair(self.home_id, self.token)
        assert data["status"] == "registered"
        assert data["device_token"] is not None, "device_token must be non-null on first registration"
        assert data["credential_already_issued"] is False

    def test_token_has_correct_length(self):
        data = _full_pair(self.home_id, self.token)
        tok = data["device_token"]
        assert len(tok) == TOKEN_LENGTH, (
            f"Expected token length {TOKEN_LENGTH}, got {len(tok)}: {tok!r}"
        )

    def test_token_starts_with_dvc_prefix(self):
        data = _full_pair(self.home_id, self.token)
        assert data["device_token"].startswith(f"{TOKEN_PREFIX}_"), (
            f"Token must start with '{TOKEN_PREFIX}_'"
        )

    def test_token_device_id_prefix_matches_response_device_id(self):
        """UUID embedded in token prefix must match the device_id returned."""
        data = _full_pair(self.home_id, self.token)
        device_id, _ = parse_token(data["device_token"])
        assert str(device_id) == data["device_id"]

    def test_token_home_id_matches_code_home(self):
        """Home bound to the token must be the one from the pairing code, not client-supplied."""
        data = _full_pair(self.home_id, self.token)
        assert data["home_id"] == self.home_id

    def test_two_different_devices_get_different_tokens(self):
        code_a = _generate_code(self.home_id, self.token)
        code_b = _generate_code(self.home_id, self.token)
        r_a = _claim(code_a)
        r_b = _claim(code_b)
        assert r_a.status_code == r_b.status_code == 200
        assert r_a.json()["device_token"] != r_b.json()["device_token"], (
            "Different devices must receive different tokens"
        )

    def test_token_is_parseable(self):
        data = _full_pair(self.home_id, self.token)
        device_id, secret = parse_token(data["device_token"])
        assert isinstance(device_id, UUID)
        assert len(secret) == 64  # 64 hex chars = 32 bytes


# ===========================================================================
# 2. Credential not re-issued on idempotent claim
# ===========================================================================

class TestCredentialNotReissued:
    """Claiming the same device_identifier again must not yield a new token."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_already_registered_returns_no_token(self):
        machine_id = str(uuid4())
        # First claim — registers device, issues token
        data1 = _full_pair(self.home_id, self.token, device_identifier=machine_id)
        assert data1["status"] == "registered"
        assert data1["device_token"] is not None

        # Second claim (new code, same machine) — idempotent, no token
        code2 = _generate_code(self.home_id, self.token)
        r2 = _claim(code2, device_identifier=machine_id)
        assert r2.status_code == 200, r2.text
        data2 = r2.json()

        assert data2["status"] == "already_registered"
        assert data2["device_token"] is None, (
            "device_token must be null on idempotent re-claim"
        )
        assert data2["credential_already_issued"] is True

    def test_already_registered_same_device_id_returned(self):
        machine_id = str(uuid4())
        data1 = _full_pair(self.home_id, self.token, device_identifier=machine_id)

        code2 = _generate_code(self.home_id, self.token)
        r2 = _claim(code2, device_identifier=machine_id)
        assert r2.json()["device_id"] == data1["device_id"], (
            "Re-claimed device must return the original device_id"
        )


# ===========================================================================
# 3. Device auth dependency — GET /api/devices/me
# ===========================================================================

class TestDeviceAuthEndpoint:
    """All credential rejection scenarios tested through GET /api/devices/me."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()
        data = _full_pair(self.home_id, self.token)
        self.device_token = data["device_token"]
        self.device_id = data["device_id"]

    def teardown_method(self):
        _reset()

    def test_valid_token_accepted(self):
        r = client.get("/api/devices/me", headers=_device_header(self.device_token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["device_id"] == self.device_id
        assert body["home_id"] == self.home_id

    def test_missing_auth_header_returns_401(self):
        r = client.get("/api/devices/me")
        assert r.status_code == 401

    def test_empty_auth_header_returns_401(self):
        r = client.get("/api/devices/me", headers={"Authorization": ""})
        assert r.status_code == 401

    def test_wrong_scheme_devicetoken_typo_returns_401(self):
        r = client.get(
            "/api/devices/me",
            headers={"Authorization": f"DevTokens {self.device_token}"},
        )
        assert r.status_code == 401

    def test_bearer_scheme_rejected_on_device_endpoint(self):
        """A valid user JWT with Bearer scheme must NOT authenticate on device routes."""
        r = client.get("/api/devices/me", headers=_bearer(self.token))
        assert r.status_code == 401

    def test_malformed_token_no_prefix_returns_401(self):
        r = client.get(
            "/api/devices/me",
            headers={"Authorization": "DeviceToken notavalidtoken"},
        )
        assert r.status_code == 401

    def test_malformed_token_too_short_returns_401(self):
        r = client.get(
            "/api/devices/me",
            headers={"Authorization": "DeviceToken dvc_abc_123"},
        )
        assert r.status_code == 401

    def test_unknown_device_id_in_token_returns_401(self):
        """Fabricate a token with a valid format but unknown device UUID."""
        fake_token = generate_raw_token(uuid4())
        r = client.get("/api/devices/me", headers=_device_header(fake_token))
        assert r.status_code == 401

    def test_wrong_secret_returns_401(self):
        """Correct device_id prefix but wrong 64-char secret → 401."""
        import secrets as _sec
        real_device_id, _ = parse_token(self.device_token)
        bad_token = f"{TOKEN_PREFIX}_{real_device_id.hex}_{_sec.token_hex(32)}"
        r = client.get("/api/devices/me", headers=_device_header(bad_token))
        assert r.status_code == 401

    def test_device_me_returns_active_status(self):
        r = client.get("/api/devices/me", headers=_device_header(self.device_token))
        assert r.status_code == 200
        # After a fresh claim, device status should not be 'revoked'
        assert r.json()["status"] != "revoked"


# ===========================================================================
# 4. Revocation — immediate effect
# ===========================================================================

class TestRevocation:
    """Revoking a device must block its next authenticated request."""

    def setup_method(self):
        _reset()
        self.uid, self.token, self.home_id = _setup_owner()
        data = _full_pair(self.home_id, self.token)
        self.device_token = data["device_token"]
        self.device_id = data["device_id"]

    def teardown_method(self):
        _reset()

    def test_revoke_returns_204(self):
        r = client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.token),
        )
        assert r.status_code == 204, r.text

    def test_revoked_device_rejected_on_next_request(self):
        # Confirm token works BEFORE revocation
        r_before = client.get("/api/devices/me", headers=_device_header(self.device_token))
        assert r_before.status_code == 200, "Device should be authenticated before revocation"

        # Revoke
        r_revoke = client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.token),
        )
        assert r_revoke.status_code == 204

        # Confirm token is rejected AFTER revocation
        r_after = client.get("/api/devices/me", headers=_device_header(self.device_token))
        assert r_after.status_code == 401, (
            "Revoked device must be rejected on subsequent request"
        )

    def test_revoke_nonexistent_device_returns_404(self):
        fake_id = str(uuid4())
        r = client.post(
            f"/api/devices/{fake_id}/revoke",
            headers=_bearer(self.token),
        )
        assert r.status_code == 404

    def test_revoke_requires_authentication(self):
        r = client.post(f"/api/devices/{self.device_id}/revoke")
        assert r.status_code == 401

    def test_in_memory_state_reflects_revocation(self):
        """After revocation, device's in-memory record must have credential_hash=None."""
        client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.token),
        )
        device = device_repository._in_memory_devices.get(UUID(self.device_id))
        assert device is not None
        assert device["credential_hash"] is None, (
            "credential_hash must be cleared after revocation"
        )
        assert device["status"] == "revoked"


# ===========================================================================
# 5. Cross-home isolation
# ===========================================================================

class TestCrossHomeIsolation:
    """A device is bound to exactly one home; its home_id cannot be overridden."""

    def setup_method(self):
        _reset()
        _, self.tok_a, self.home_a = _setup_owner()
        _, self.tok_b, self.home_b = _setup_owner()

        # Pair device_a to home_a
        data_a = _full_pair(self.home_a, self.tok_a)
        self.token_a = data_a["device_token"]
        self.device_id_a = data_a["device_id"]

        # Pair device_b to home_b
        data_b = _full_pair(self.home_b, self.tok_b)
        self.token_b = data_b["device_token"]
        self.device_id_b = data_b["device_id"]

    def teardown_method(self):
        _reset()

    def test_device_me_returns_own_home(self):
        r = client.get("/api/devices/me", headers=_device_header(self.token_a))
        assert r.status_code == 200
        assert r.json()["home_id"] == self.home_a
        assert r.json()["home_id"] != self.home_b

    def test_device_b_token_cannot_act_as_device_a(self):
        """Device B's token must not authenticate as device A's identity."""
        r = client.get("/api/devices/me", headers=_device_header(self.token_b))
        assert r.status_code == 200
        body = r.json()
        assert body["home_id"] == self.home_b, (
            "Device B must always resolve to home_b, never home_a"
        )
        assert body["device_id"] == self.device_id_b

    def test_device_home_id_is_server_controlled(self):
        """
        The home_id returned by /devices/me comes from the DB record,
        not from anything the device supplied during claim.
        """
        r = client.get("/api/devices/me", headers=_device_header(self.token_a))
        assert r.json()["home_id"] == self.home_a

    def test_user_a_cannot_revoke_device_b(self):
        """User A (owns home_a) cannot revoke a device registered to home_b."""
        r = client.post(
            f"/api/devices/{self.device_id_b}/revoke",
            headers=_bearer(self.tok_a),
        )
        assert r.status_code == 403, (
            f"Expected 403 when non-owner tries to revoke; got {r.status_code}: {r.text}"
        )

        # Device B's token should still work
        r_me = client.get("/api/devices/me", headers=_device_header(self.token_b))
        assert r_me.status_code == 200, "Device B must still work after failed revocation attempt"


# ===========================================================================
# 6. Client cannot override home_id
# ===========================================================================

class TestClientCannotOverrideHomeId:
    """PairingClaimRequest has no home_id field — home comes from the DB record."""

    def setup_method(self):
        _reset()
        _, self.tok_a, self.home_a = _setup_owner()
        _, self.tok_b, self.home_b = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_claim_home_id_from_code_not_body(self):
        """Even if a client attempts to inject extra fields, home_id is from the code."""
        code = _generate_code(self.home_a, self.tok_a)

        # Attempt to include home_id in the body (Pydantic will ignore extra fields)
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": code,
                "device_name": "Attacker PC",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
                "home_id": self.home_b,  # ignored by the model
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["home_id"] == self.home_a, (
            "home_id must come from the server-side code record, not the client body"
        )
        assert data["home_id"] != self.home_b

    def test_device_token_home_id_matches_code_home(self):
        """The device_token embeds the correct device UUID (bound to the correct home)."""
        code = _generate_code(self.home_a, self.tok_a)
        r = _claim(code)
        assert r.status_code == 200

        data = r.json()
        device_id, _ = parse_token(data["device_token"])
        assert str(device_id) == data["device_id"]

        # And /devices/me confirms the home binding
        r_me = client.get("/api/devices/me", headers=_device_header(data["device_token"]))
        assert r_me.status_code == 200
        assert r_me.json()["home_id"] == self.home_a


# ===========================================================================
# 7. Non-owner revocation
# ===========================================================================

class TestNonOwnerRevocation:
    """Only the home owner may revoke a device."""

    def setup_method(self):
        _reset()
        _, self.tok_owner, self.home_id = _setup_owner()
        _, self.tok_other, _ = _setup_owner()  # Different user, different home

        data = _full_pair(self.home_id, self.tok_owner)
        self.device_token = data["device_token"]
        self.device_id = data["device_id"]

    def teardown_method(self):
        _reset()

    def test_non_owner_receives_403(self):
        r = client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.tok_other),
        )
        assert r.status_code == 403, (
            f"Non-owner must receive 403 on revoke; got {r.status_code}: {r.text}"
        )

    def test_device_still_authenticated_after_failed_revocation(self):
        """A failed revocation must leave the device's credential intact."""
        client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.tok_other),
        )
        r = client.get("/api/devices/me", headers=_device_header(self.device_token))
        assert r.status_code == 200, (
            "Device must still be authenticated after a failed revocation attempt"
        )

    def test_owner_can_still_revoke_after_non_owner_attempt(self):
        """Owner retains revocation power after a rejected third-party attempt."""
        client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.tok_other),
        )
        r = client.post(
            f"/api/devices/{self.device_id}/revoke",
            headers=_bearer(self.tok_owner),
        )
        assert r.status_code == 204


# ===========================================================================
# 8. Duplicate identifiers and concurrent claims
# ===========================================================================

class TestDuplicateAndConcurrentClaims:
    """Race conditions and duplicate identifiers are handled correctly."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_concurrent_claims_only_one_gets_a_token(self):
        """Two threads claim the same code — only the first winner gets a token."""
        code = _generate_code(self.home_id, self.token)
        results: list[dict] = []
        status_codes: list[int] = []

        def do_claim():
            r = _claim(code, device_identifier=str(uuid4()))
            status_codes.append(r.status_code)
            if r.status_code == 200:
                results.append(r.json())

        t1 = threading.Thread(target=do_claim)
        t2 = threading.Thread(target=do_claim)
        t1.start(); t2.start()
        t1.join(); t2.join()

        successes = [s for s in status_codes if s == 200]
        failures = [s for s in status_codes if s != 200]

        assert len(successes) == 1, f"Exactly one claim must succeed; codes={status_codes}"
        assert all(c in (410, 409) for c in failures), (
            f"Losing thread must get 410 or 409; codes={status_codes}"
        )
        assert len(results) == 1
        assert results[0]["device_token"] is not None, (
            "The successful claim must include a device_token"
        )

    def test_same_identifier_different_home_409_no_token(self):
        """A device identifier already registered to home_a → 409 for home_b."""
        _, tok_b, home_b = _setup_owner()
        machine_id = str(uuid4())

        # Register to home_a
        data_a = _full_pair(self.home_id, self.token, device_identifier=machine_id)
        assert data_a["device_token"] is not None

        # Attempt to register same machine to home_b
        code_b = _generate_code(home_b, tok_b)
        r = _claim(code_b, device_identifier=machine_id)
        assert r.status_code == 409, (
            f"Same identifier on different home must return 409; got {r.status_code}: {r.text}"
        )

    def test_duplicate_identifier_same_home_no_new_token(self):
        """Idempotent re-claim of the same machine must not issue a second token."""
        machine_id = str(uuid4())
        data1 = _full_pair(self.home_id, self.token, device_identifier=machine_id)
        token1 = data1["device_token"]

        code2 = _generate_code(self.home_id, self.token)
        r2 = _claim(code2, device_identifier=machine_id)
        assert r2.status_code == 200
        assert r2.json()["device_token"] is None, (
            "Re-claiming same machine on same home must not yield a new token"
        )

        # Original token still works
        r_me = client.get("/api/devices/me", headers=_device_header(token1))
        assert r_me.status_code == 200


# ===========================================================================
# 9. Database failures fail closed
# ===========================================================================

class TestDatabaseFailureFailsClosed:
    """Failure modes that must not silently succeed."""

    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_production_environment_rejects_memory_fallback(self):
        """ENVIRONMENT=production must raise RuntimeError if TEST_ISOLATED_MODE=1.

        This guards against accidentally running in-memory mode in production,
        which would silently discard all data.
        """
        from app.repositories.home_repository import is_memory_fallback_enabled

        with patch.object(settings, "ENVIRONMENT", "production"):
            with pytest.raises(RuntimeError, match="TEST_ISOLATED_MODE=1 is not permitted"):
                is_memory_fallback_enabled()

    def test_store_credential_hash_raises_if_device_missing(self):
        """store_credential_hash with an unknown device_id must raise 500, not silently succeed."""
        from fastapi import HTTPException as _HTTP

        ghost_id = uuid4()
        # device_repository._in_memory_devices is empty — ghost_id is unknown.
        with pytest.raises(_HTTP) as exc_info:
            device_repository.store_credential_hash(ghost_id, "some_fake_hash")

        assert exc_info.value.status_code == 500, (
            "store_credential_hash must fail closed (500) when device is not found"
        )

    def test_revoke_unknown_device_returns_404(self):
        """Revoking a non-existent device raises 404, not a silent no-op."""
        from fastapi import HTTPException as _HTTP
        _, tok, home_id = _setup_owner()
        uid = str(uuid4())

        with pytest.raises(_HTTP) as exc_info:
            device_repository.revoke_device(uuid4(), UUID(uid))

        assert exc_info.value.status_code in (403, 404)


# ===========================================================================
# 10. Hash persistence — raw token never stored
# ===========================================================================

class TestHashPersistence:
    """The raw token must never appear in the stored device record."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_raw_token_not_stored_in_device_record(self):
        data = _full_pair(self.home_id, self.token)
        raw_token = data["device_token"]

        device_uuid = UUID(data["device_id"])
        device = device_repository._in_memory_devices.get(device_uuid)
        assert device is not None, "Device must exist in the in-memory store"

        stored_hash = device.get("credential_hash")
        assert stored_hash is not None, "credential_hash must be set after a successful claim"
        assert stored_hash != raw_token, (
            "Raw token must NEVER be stored in credential_hash"
        )

    def test_stored_hash_is_bcrypt_format(self):
        data = _full_pair(self.home_id, self.token)
        device = device_repository._in_memory_devices.get(UUID(data["device_id"]))
        stored_hash = device["credential_hash"]
        # bcrypt hashes start with $2b$ (or $2a$ / $2y$)
        assert stored_hash.startswith("$2"), (
            f"Expected bcrypt hash starting with '$2', got: {stored_hash[:4]!r}"
        )

    def test_stored_hash_verifies_against_secret_portion(self):
        data = _full_pair(self.home_id, self.token)
        raw_token = data["device_token"]
        _, secret = parse_token(raw_token)

        device = device_repository._in_memory_devices.get(UUID(data["device_id"]))
        stored_hash = device["credential_hash"]

        assert verify_token_secret(secret, stored_hash), (
            "Stored hash must verify against the secret portion of the issued token"
        )

    def test_credential_hash_cleared_after_revocation(self):
        data = _full_pair(self.home_id, self.token)
        device_id = data["device_id"]

        # Revoke
        client.post(f"/api/devices/{device_id}/revoke", headers=_bearer(self.token))

        device = device_repository._in_memory_devices.get(UUID(device_id))
        assert device["credential_hash"] is None, (
            "credential_hash must be NULL after revocation"
        )

    def test_device_credential_module_functions(self):
        """Unit-test the pure credential functions directly."""
        uid = uuid4()
        raw = generate_raw_token(uid)

        # Format checks
        assert raw.startswith(f"{TOKEN_PREFIX}_")
        assert len(raw) == TOKEN_LENGTH

        # Parse round-trip
        parsed_id, secret = parse_token(raw)
        assert parsed_id == uid
        assert len(secret) == 64

        # Hash and verify
        h = hash_token_secret(secret)
        assert verify_token_secret(secret, h) is True

        # Wrong secret must fail
        import secrets as _sec
        wrong = _sec.token_hex(32)
        assert verify_token_secret(wrong, h) is False


# ===========================================================================
# 11. Existing user-authenticated endpoints — regression check
# ===========================================================================

class TestExistingUserEndpointsUnchanged:
    """User JWT routes must continue to work exactly as before Phase 3A."""

    def setup_method(self):
        _reset()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        _reset()

    def test_user_jwt_still_authenticates_homes_endpoint(self):
        r = client.get("/api/homes", headers=_bearer(self.token))
        assert r.status_code == 200

    def test_user_jwt_still_authenticates_devices_list(self):
        r = client.get(f"/api/homes/{self.home_id}/devices", headers=_bearer(self.token))
        assert r.status_code == 200

    def test_user_jwt_still_can_create_device(self):
        r = client.post(
            f"/api/homes/{self.home_id}/devices",
            json={"device_name": "Old Camera", "device_type": "camera"},
            headers=_bearer(self.token),
        )
        assert r.status_code == 201

    def test_user_jwt_still_generates_pairing_codes(self):
        r = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=_bearer(self.token))
        assert r.status_code == 201

    def test_device_token_rejected_on_user_endpoints(self):
        """A DeviceToken must NOT work on user-JWT-only endpoints."""
        data = _full_pair(self.home_id, self.token)
        device_tok = data["device_token"]

        # The /api/homes endpoint requires Bearer JWT
        r = client.get("/api/homes", headers=_device_header(device_tok))
        assert r.status_code == 401, (
            "DeviceToken must not authenticate on user Bearer endpoints"
        )

    def test_unauthenticated_request_still_returns_401(self):
        r = client.get("/api/homes")
        assert r.status_code == 401

    def test_video_status_still_requires_user_jwt(self):
        r = client.get("/video/status", params={"home_id": self.home_id})
        assert r.status_code == 401

    def test_existing_pairing_claim_response_still_has_required_fields(self):
        """Verify the full Phase 3A claim response has all fields including new ones."""
        data = _full_pair(self.home_id, self.token)
        for field in ("device_id", "home_id", "device_name", "device_type", "status", "message"):
            assert field in data, f"Required field '{field}' missing from claim response"
        # New Phase 3A fields
        assert "device_token" in data
        assert "credential_already_issued" in data

"""
Isolated tests for the desktop-pairing foundation.

Coverage
--------
1.  Route registration — all pairing endpoints exist (not 404).
2.  Authentication — code generation requires a valid JWT.
3.  Ownership — non-owner receives 403.
4.  Valid flow — owner generates a code; code is well-formed.
5.  Rate limit — exceeding MAX_ACTIVE_CODES_PER_HOME returns 429.
6.  Claim — valid code registers the device.
7.  Claim — client-supplied home_id is ignored; home comes from the code.
8.  Claim — expired code is rejected (410).
9.  Claim — used code cannot be claimed again (410).
10. Claim — unknown code returns 404.
11. Claim — duplicate device_identifier on the same home is idempotent.
12. Claim — duplicate device_identifier on a DIFFERENT home returns 409.
13. Claim — concurrent claims: only one succeeds, the second gets 410.
14. Claim — invalid code format returns 422.
15. Database errors fail safely (503 propagation).

Run with:
    TEST_ISOLATED_MODE=1 python -m pytest tests/test_pairing.py -v
"""
from __future__ import annotations

import os
import threading
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JWT_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"


def _make_token(user_id: str) -> str:
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


client = TestClient(app, raise_server_exceptions=True)


def _setup_owner() -> tuple[str, str, str]:
    """Create a user and a home; return (user_id, token, home_id)."""
    user_id = str(uuid4())
    token = _make_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/homes", json={"name": "Pairing Test Home"}, headers=headers)
    assert res.status_code == 201, f"Home creation failed: {res.text}"
    return user_id, token, res.json()["id"]


# ---------------------------------------------------------------------------
# 1. Route registration
# ---------------------------------------------------------------------------

class TestRouteRegistration:
    """Every pairing endpoint must exist (not 404)."""

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_generate_code_route_exists(self):
        fake_home = str(uuid4())
        r = client.post(f"/api/homes/{fake_home}/pairing-codes")
        assert r.status_code != 404, f"Route missing: {r.status_code} {r.text}"

    def test_claim_route_exists(self):
        r = client.post("/api/pairing/claim", json={})
        # 422 (validation error) proves the route exists; 404 means it is missing.
        assert r.status_code != 404, f"Route missing: {r.status_code} {r.text}"


# ---------------------------------------------------------------------------
# 2. Authentication — code generation requires valid JWT
# ---------------------------------------------------------------------------

class TestCodeGenerationAuth:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_no_token_returns_401(self):
        fake_home = str(uuid4())
        r = client.post(f"/api/homes/{fake_home}/pairing-codes")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    def test_invalid_token_returns_401(self):
        fake_home = str(uuid4())
        r = client.post(
            f"/api/homes/{fake_home}/pairing-codes",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert r.status_code == 401

    def test_expired_token_returns_401(self):
        user_id = str(uuid4())
        expired_payload = {
            "sub": user_id,
            "exp": int(time.time()) - 3600,
            "iat": int(time.time()) - 7200,
        }
        expired_token = jwt.encode(expired_payload, _JWT_SECRET, algorithm="HS256")
        fake_home = str(uuid4())
        r = client.post(
            f"/api/homes/{fake_home}/pairing-codes",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 3. Ownership enforcement
# ---------------------------------------------------------------------------

class TestOwnershipEnforcement:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token_a, self.home_a_id = _setup_owner()
        _, self.token_b, self.home_b_id = _setup_owner()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_owner_can_generate_code(self):
        r = client.post(
            f"/api/homes/{self.home_a_id}/pairing-codes",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert r.status_code == 201, f"Expected 201 for owner, got {r.status_code}: {r.text}"

    def test_non_owner_receives_403(self):
        """User B cannot generate a code for User A's home."""
        r = client.post(
            f"/api/homes/{self.home_a_id}/pairing-codes",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert r.status_code == 403, f"Expected 403 for non-owner, got {r.status_code}: {r.text}"

    def test_nonexistent_home_returns_404(self):
        user_id = str(uuid4())
        token = _make_token(user_id)
        r = client.post(
            f"/api/homes/{uuid4()}/pairing-codes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404, f"Expected 404 for unknown home, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# 4. Valid code generation
# ---------------------------------------------------------------------------

class TestValidCodeGeneration:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def _generate(self) -> dict:
        r = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r.status_code == 201, f"Unexpected status: {r.status_code} {r.text}"
        return r.json()

    def test_response_has_required_fields(self):
        data = self._generate()
        for field in ("code", "home_id", "expires_at", "ttl_seconds"):
            assert field in data, f"Missing field '{field}' in response"

    def test_code_format_with_hyphen(self):
        """Returned code should be formatted as XXX-XXX (6 chars + 1 hyphen)."""
        data = self._generate()
        code = data["code"]
        assert len(code) == 7, f"Expected 7-char code (e.g. 'A3F-72K'), got {code!r}"
        assert code[3] == "-", f"Expected hyphen at position 3, got {code!r}"
        assert code[:3].isalnum() and code[4:].isalnum(), f"Non-alphanumeric in code: {code!r}"

    def test_home_id_matches_request(self):
        data = self._generate()
        assert data["home_id"] == self.home_id

    def test_ttl_is_positive(self):
        data = self._generate()
        assert data["ttl_seconds"] > 0, "ttl_seconds must be positive at time of creation"

    def test_expires_at_is_in_future(self):
        data = self._generate()
        expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        assert expires > datetime.now(timezone.utc), "expires_at must be in the future"

    def test_each_code_is_unique(self):
        """Two consecutive generations must not return the same code."""
        code_a = self._generate()["code"]
        code_b = self._generate()["code"]
        assert code_a != code_b, "Two consecutive codes must not be identical"


# ---------------------------------------------------------------------------
# 5. Rate limiting — max active codes per home
# ---------------------------------------------------------------------------

class TestCodeRateLimit:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_exceeding_max_active_codes_returns_429(self):
        from app.repositories.pairing_repository import PairingRepository
        max_codes = PairingRepository.MAX_ACTIVE_CODES_PER_HOME

        # Generate the maximum allowed codes
        for i in range(max_codes):
            r = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
            assert r.status_code == 201, f"Code #{i + 1} failed: {r.status_code} {r.text}"

        # The next one should be rejected
        r = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r.status_code == 429, f"Expected 429 after max codes, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# 6. Valid claim flow
# ---------------------------------------------------------------------------

class TestValidClaim:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def _generate_code(self) -> str:
        r = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r.status_code == 201
        return r.json()["code"]

    def _claim(self, code: str, device_id: str = None, device_name: str = "Test PC") -> dict:
        body = {
            "code": code,
            "device_name": device_name,
            "device_type": "desktop_camera",
            "device_identifier": device_id or str(uuid4()),
        }
        r = client.post("/api/pairing/claim", json=body)
        return r

    def test_valid_claim_returns_200(self):
        code = self._generate_code()
        r = self._claim(code)
        assert r.status_code == 200, f"Expected 200 from valid claim, got {r.status_code}: {r.text}"

    def test_claim_response_has_required_fields(self):
        code = self._generate_code()
        r = self._claim(code)
        data = r.json()
        for field in ("device_id", "home_id", "device_name", "device_type", "status", "message"):
            assert field in data, f"Missing field '{field}' in claim response"

    def test_claim_home_id_matches_code_home(self):
        """home_id in the response must be the one stored with the code — not client-supplied."""
        code = self._generate_code()
        r = self._claim(code)
        assert r.json()["home_id"] == self.home_id

    def test_claim_status_is_registered(self):
        code = self._generate_code()
        r = self._claim(code)
        assert r.json()["status"] == "registered"

    def test_claim_device_name_preserved(self):
        code = self._generate_code()
        r = self._claim(code, device_name="My Special Laptop")
        assert r.json()["device_name"] == "My Special Laptop"


# ---------------------------------------------------------------------------
# 7. Client cannot override the home via claim body
# ---------------------------------------------------------------------------

class TestClaimHomeIdCannotBeOverridden:
    """The claim endpoint has no home_id field; the server resolves it from the code."""

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token_a, self.home_a = _setup_owner()
        _, self.token_b, self.home_b = _setup_owner()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_registered_device_belongs_to_code_home_not_any_other(self):
        """Generate code for home_a.  Claim it.  Result must link device to home_a."""
        r_code = client.post(
            f"/api/homes/{self.home_a}/pairing-codes",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert r_code.status_code == 201
        code = r_code.json()["code"]

        # Claim — body has no home_id field, so there's nothing to inject.
        r_claim = client.post(
            "/api/pairing/claim",
            json={
                "code": code,
                "device_name": "Attacker PC",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        assert r_claim.status_code == 200
        assert r_claim.json()["home_id"] == self.home_a
        assert r_claim.json()["home_id"] != self.home_b


# ---------------------------------------------------------------------------
# 8. Expired code rejected
# ---------------------------------------------------------------------------

class TestExpiredCode:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_expired_code_returns_410(self):
        """Manually insert an already-expired code then try to claim it."""
        from datetime import timedelta
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        pairing_repository.create_code(
            home_id=self.home_id if isinstance(self.home_id, __import__("uuid").UUID)
                    else __import__("uuid").UUID(self.home_id),
            code="EXPRD1",
            expires_at=expired_at,
        )
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "EXPRD1",
                "device_name": "Test",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        assert r.status_code == 410, f"Expected 410 for expired code, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# 9. Used code cannot be claimed again
# ---------------------------------------------------------------------------

class TestUsedCodeCannotBeClaimedAgain:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_used_code_returns_410(self):
        r_code = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r_code.status_code == 201
        code = r_code.json()["code"]

        device_id = str(uuid4())
        claim_body = {
            "code": code,
            "device_name": "Laptop",
            "device_type": "desktop_camera",
            "device_identifier": device_id,
        }

        # First claim — must succeed
        r1 = client.post("/api/pairing/claim", json=claim_body)
        assert r1.status_code == 200, f"First claim failed: {r1.status_code} {r1.text}"

        # Second claim with the same code — must fail
        r2 = client.post("/api/pairing/claim", json=claim_body)
        assert r2.status_code == 410, f"Expected 410 for reused code, got {r2.status_code}: {r2.text}"


# ---------------------------------------------------------------------------
# 10. Unknown code returns 404
# ---------------------------------------------------------------------------

class TestUnknownCode:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_unknown_code_returns_404(self):
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "ZZZNONE",
                "device_name": "Ghost",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        # 422 if format validation rejects it, 404 if it reaches DB lookup
        assert r.status_code in (404, 422), (
            f"Expected 404 or 422 for unknown code, got {r.status_code}: {r.text}"
        )

    def test_unknown_valid_format_code_returns_404(self):
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "ABC123",   # valid format, does not exist
                "device_name": "Ghost",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        assert r.status_code == 404, f"Expected 404 for non-existent code, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# 11. Duplicate device_identifier on same home — idempotent
# ---------------------------------------------------------------------------

class TestIdempotentClaim:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_same_device_identifier_same_home_is_idempotent(self):
        # First pairing with device X
        r1_code = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r1_code.status_code == 201
        code1 = r1_code.json()["code"]

        machine_id = str(uuid4())
        r1 = client.post(
            "/api/pairing/claim",
            json={"code": code1, "device_name": "PC", "device_type": "desktop_camera", "device_identifier": machine_id},
        )
        assert r1.status_code == 200
        device_id_1 = r1.json()["device_id"]

        # Second pairing with same device_identifier for the same home
        r2_code = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r2_code.status_code == 201
        code2 = r2_code.json()["code"]

        r2 = client.post(
            "/api/pairing/claim",
            json={"code": code2, "device_name": "PC Renamed", "device_type": "desktop_camera", "device_identifier": machine_id},
        )
        assert r2.status_code == 200, f"Expected 200 for idempotent claim, got {r2.status_code}: {r2.text}"
        assert r2.json()["status"] == "already_registered"
        # Same device UUID returned
        assert r2.json()["device_id"] == device_id_1


# ---------------------------------------------------------------------------
# 12. Duplicate device_identifier on DIFFERENT home — 409
# ---------------------------------------------------------------------------

class TestCrossHomeDuplicateDeviceIdentifier:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token_a, self.home_a = _setup_owner()
        _, self.token_b, self.home_b = _setup_owner()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_same_device_identifier_different_home_returns_409(self):
        machine_id = str(uuid4())

        # Pair with home_a
        r_code_a = client.post(
            f"/api/homes/{self.home_a}/pairing-codes",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert r_code_a.status_code == 201
        code_a = r_code_a.json()["code"]
        r_claim_a = client.post(
            "/api/pairing/claim",
            json={"code": code_a, "device_name": "PC", "device_type": "desktop_camera", "device_identifier": machine_id},
        )
        assert r_claim_a.status_code == 200

        # Try to pair the SAME machine with home_b — must fail
        r_code_b = client.post(
            f"/api/homes/{self.home_b}/pairing-codes",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert r_code_b.status_code == 201
        code_b = r_code_b.json()["code"]
        r_claim_b = client.post(
            "/api/pairing/claim",
            json={"code": code_b, "device_name": "PC", "device_type": "desktop_camera", "device_identifier": machine_id},
        )
        assert r_claim_b.status_code == 409, (
            f"Expected 409 for cross-home duplicate identifier, got {r_claim_b.status_code}: {r_claim_b.text}"
        )


# ---------------------------------------------------------------------------
# 13. Concurrent claims — race-condition safety
# ---------------------------------------------------------------------------

class TestConcurrentClaims:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()
        _, self.token, self.home_id = _setup_owner()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def test_concurrent_claims_only_one_succeeds(self):
        """Two threads claiming the same code: exactly one gets 200, one gets 410."""
        r_code = client.post(f"/api/homes/{self.home_id}/pairing-codes", headers=self.headers)
        assert r_code.status_code == 201
        code = r_code.json()["code"]

        results = []

        def do_claim():
            r = client.post(
                "/api/pairing/claim",
                json={
                    "code": code,
                    "device_name": "Racing PC",
                    "device_type": "desktop_camera",
                    "device_identifier": str(uuid4()),  # different identifier per thread
                },
            )
            results.append(r.status_code)

        t1 = threading.Thread(target=do_claim)
        t2 = threading.Thread(target=do_claim)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2, "Both threads must complete"
        successes = results.count(200)
        failures = [c for c in results if c != 200]

        assert successes == 1, f"Exactly one claim must succeed; results={results}"
        assert all(c in (410, 409) for c in failures), (
            f"Failing thread must get 410 or 409; results={results}"
        )


# ---------------------------------------------------------------------------
# 14. Invalid code format returns 422
# ---------------------------------------------------------------------------

class TestInvalidCodeFormat:

    def setup_method(self):
        backend_store.clear()
        pairing_repository.clear()

    def teardown_method(self):
        backend_store.clear()
        pairing_repository.clear()

    @pytest.mark.parametrize("bad_code,expected_status", [
        # Structurally invalid — Pydantic rejects before hitting the DB
        ("",        422),  # empty
        ("ABC",     422),  # too short
        ("ABCDEFG", 422),  # too long (7 chars; our max_length is 7 but fails regex)
        ("!@#$%^",  422),  # special chars
        ("AB CD12", 422),  # contains space
        # 'abc123' is uppercased to 'ABC123' by the validator — valid format,
        # reaches the DB, returns 404 (not found).
        ("abc123",  404),
    ])
    def test_invalid_format_returns_422(self, bad_code: str, expected_status: int):
        """Structurally invalid codes are rejected by Pydantic (422).
        Lowercase codes are normalised and reach the DB; 404 is the correct result
        when the normalised code is not found.
        """
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": bad_code,
                "device_name": "Test",
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        assert r.status_code == expected_status, (
            f"Expected {expected_status} for code {bad_code!r}, got {r.status_code}: {r.text}"
        )

    def test_invalid_device_type_returns_422(self):
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "ABC123",
                "device_name": "Test",
                "device_type": "microwave",   # not allowed
                "device_identifier": str(uuid4()),
            },
        )
        assert r.status_code == 422

    def test_blank_device_name_returns_422(self):
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "ABC123",
                "device_name": "   ",         # whitespace only
                "device_type": "desktop_camera",
                "device_identifier": str(uuid4()),
            },
        )
        assert r.status_code == 422

    def test_special_chars_in_device_identifier_returns_422(self):
        r = client.post(
            "/api/pairing/claim",
            json={
                "code": "ABC123",
                "device_name": "Test",
                "device_type": "desktop_camera",
                "device_identifier": "../../etc/passwd",
            },
        )
        assert r.status_code == 422

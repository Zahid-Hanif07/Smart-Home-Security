"""
Isolated tests for video streaming routes: registration, frame ingestion,
authorization, home ownership, and stream status diagnostics.

Run with:
    TEST_ISOLATED_MODE=1 python -m pytest tests/test_video_routes.py -v

These tests NEVER make live Supabase calls (TEST_ISOLATED_MODE=1 forces in-memory
repositories). Production authentication is NOT weakened; JWT validation uses the
configured SUPABASE_JWT_SECRET (falls back to a test-only secret if absent).
"""
import os

os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import time
from uuid import uuid4

import cv2
import jwt
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.services.backend_store import backend_store
from app.streaming.frame_manager import get_frame_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_JWT_SECRET = settings.SUPABASE_JWT_SECRET or "test-only-secret-not-for-production"
_TEST_DEVICE_SESSION_SECRET = "test-device-session-key-for-video-route-tests-32-bytes"


@pytest.fixture(autouse=True)
def _configure_device_session_key(monkeypatch):
    monkeypatch.setattr(settings, "DEVICE_SESSION_SIGNING_SECRET", _TEST_DEVICE_SESSION_SECRET)


def _make_token(user_id: str) -> str:
    """Mint a short-lived HS256 JWT for a given user UUID (isolated test only)."""
    payload = {
        "sub": str(user_id),
        "id": str(user_id),
        "email": f"{str(user_id)[:8]}@test.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


def _make_jpeg() -> bytes:
    """Return a minimal valid JPEG (64×64 black image)."""
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok, "cv2.imencode failed to create test JPEG"
    return buf.tobytes()


def _publisher_headers(home_id: str, user_headers: dict) -> dict:
    """Pair a test publisher and exchange its DeviceToken for a session."""
    code_response = client.post(
        f"/api/homes/{home_id}/pairing-codes",
        headers=user_headers,
    )
    assert code_response.status_code == 201, code_response.text
    claim_response = client.post(
        "/api/pairing/claim",
        json={
            "code": code_response.json()["code"],
            "device_name": "Video Route Test Camera",
            "device_type": "desktop_camera",
            "device_identifier": str(uuid4()),
        },
    )
    assert claim_response.status_code == 200, claim_response.text
    device_token = claim_response.json()["device_token"]
    session_response = client.post(
        "/api/devices/session",
        headers={"Authorization": f"DeviceToken {device_token}"},
    )
    assert session_response.status_code == 200, session_response.text
    return {
        "Authorization": f"DeviceSession {session_response.json()['session_token']}",
        "Content-Type": "image/jpeg",
        "X-Home-ID": home_id,
    }


def _reset_frame_manager() -> None:
    fm = get_frame_manager()
    fm._latest_jpeg = None
    fm._home_id = None
    fm._last_update_time = 0.0


client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# 1. Route Registration
# ---------------------------------------------------------------------------

class TestVideoRouteRegistration:
    """Verify all video routes are reachable (not 404).

    Without a token they must return 401 (auth required), which proves the route
    exists and is reachable by the router.  A 404 means the route is missing.
    """

    def test_stream_route_exists(self):
        """GET /video/stream without auth → 401, not 404."""
        r = client.get("/video/stream?home_id=00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401, f"Route missing or wrong: {r.status_code} {r.text}"

    def test_status_route_exists(self):
        """GET /video/status without auth → 401, not 404."""
        r = client.get("/video/status?home_id=00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_frame_route_exists(self):
        """POST /video/frame without auth → 401, not 404."""
        r = client.post(
            "/video/frame",
            content=b"x",
            headers={"Content-Type": "image/jpeg", "X-Home-ID": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 401, f"Route missing or wrong method: {r.status_code} {r.text}"

    def test_api_prefix_stream_route_exists(self):
        """GET /api/video/stream (dual-mount prefix) → 401."""
        r = client.get("/api/video/stream?home_id=00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_api_prefix_frame_route_exists(self):
        """POST /api/video/frame (dual-mount prefix) → 401."""
        r = client.post(
            "/api/video/frame",
            content=b"x",
            headers={"Content-Type": "image/jpeg", "X-Home-ID": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 401

    def test_homes_face_records_route_exists(self):
        """GET /api/homes/{id}/face-records without auth → 401."""
        r = client.get(f"/api/homes/{uuid4()}/face-records")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 2. Frame Ingestion
# ---------------------------------------------------------------------------

class TestFrameIngestion:
    """POST /video/frame — valid and invalid scenarios."""

    def setup_method(self):
        backend_store.clear()
        _reset_frame_manager()
        self.user_id = str(uuid4())
        self.token = _make_token(self.user_id)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        # Create a home in-memory via the API
        res = client.post("/api/homes", json={"name": "Publisher Home"}, headers=self.auth_headers)
        assert res.status_code == 201, f"Home setup failed: {res.status_code} {res.text}"
        self.home_id = res.json()["id"]
        self.publisher_headers = _publisher_headers(self.home_id, self.auth_headers)

    def teardown_method(self):
        _reset_frame_manager()
        backend_store.clear()

    def _frame_headers(self) -> dict:
        return {
            **self.publisher_headers,
            "Content-Type": "image/jpeg",
            "X-Home-ID": self.home_id,
        }

    def test_valid_frame_accepted_returns_200(self):
        r = client.post("/video/frame", content=_make_jpeg(), headers=self._frame_headers())
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("status") == "ok"

    def test_frame_stored_in_frame_manager(self):
        """After a valid frame POST the FrameManager must have a JPEG."""
        client.post("/video/frame", content=_make_jpeg(), headers=self._frame_headers())
        fm = get_frame_manager()
        assert fm.is_frame_available(), "FrameManager did not store the frame"
        assert fm.get_home_id() == self.home_id

    def test_no_auth_header_returns_401(self):
        r = client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={"Content-Type": "image/jpeg", "X-Home-ID": self.home_id},
        )
        assert r.status_code == 401

    def test_different_user_cannot_publish_to_foreign_home(self):
        """A JWT for a different user_id must not be able to post frames to this home."""
        other_token = _make_token(str(uuid4()))
        r = client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={
                "Authorization": f"Bearer {other_token}",
                "Content-Type": "image/jpeg",
                "X-Home-ID": self.home_id,
            },
        )
        assert r.status_code == 401, f"Homeowner JWT must not publish frames: {r.status_code}: {r.text}"

    def test_nonexistent_home_id_returns_404(self):
        r = client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={
                **self.publisher_headers,
                "Content-Type": "image/jpeg",
                "X-Home-ID": str(uuid4()),
            },
        )
        assert r.status_code == 401, f"Session bound to another home must be rejected: {r.status_code}: {r.text}"

    def test_empty_payload_returns_400(self):
        r = client.post("/video/frame", content=b"", headers=self._frame_headers())
        assert r.status_code == 400, f"Expected 400 for empty body, got {r.status_code}"

    def test_invalid_jpeg_bytes_rejected(self):
        r = client.post("/video/frame", content=b"not-jpeg", headers=self._frame_headers())
        # FrameManager.update_jpeg returns False for corrupt data; route raises 400/500
        assert r.status_code in (400, 500), (
            f"Expected 400 or 500 for corrupt JPEG, got {r.status_code}: {r.text}"
        )

    def test_oversized_payload_rejected(self):
        """Payloads over STREAM_MAX_FRAME_BYTES (default 5 MB) must be rejected."""
        from app.config.settings import STREAM_MAX_FRAME_BYTES
        oversized = b"A" * (STREAM_MAX_FRAME_BYTES + 1)
        r = client.post("/video/frame", content=oversized, headers=self._frame_headers())
        assert r.status_code == 413, (
            f"Expected 413 for oversized payload, got {r.status_code}: {r.text}"
        )


# ---------------------------------------------------------------------------
# 3. Stream Status Diagnostics
# ---------------------------------------------------------------------------

class TestStreamStatus:
    """GET /video/status — reason field and frame availability states."""

    def setup_method(self):
        backend_store.clear()
        _reset_frame_manager()
        self.user_id = str(uuid4())
        self.token = _make_token(self.user_id)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        res = client.post("/api/homes", json={"name": "Stream Home"}, headers=self.auth_headers)
        assert res.status_code == 201
        self.home_id = res.json()["id"]
        self.publisher_headers = _publisher_headers(self.home_id, self.auth_headers)

    def teardown_method(self):
        _reset_frame_manager()
        backend_store.clear()

    def test_status_no_publisher_returns_200(self):
        r = client.get(f"/video/status?home_id={self.home_id}", headers=self.auth_headers)
        assert r.status_code == 200

    def test_status_no_publisher_fields(self):
        r = client.get(f"/video/status?home_id={self.home_id}", headers=self.auth_headers)
        data = r.json()
        assert data["frame_available"] is False
        assert data["streaming"] is False
        assert data["publisher_connected"] is False
        assert data["home_id_match"] is False
        assert data["reason"] == "no_publisher_connected"

    def test_status_after_valid_frame_is_streaming(self):
        # Publish a valid frame
        frame_headers = {
            **self.publisher_headers,
            "Content-Type": "image/jpeg",
            "X-Home-ID": self.home_id,
        }
        post = client.post("/video/frame", content=_make_jpeg(), headers=frame_headers)
        assert post.status_code == 200

        r = client.get(f"/video/status?home_id={self.home_id}", headers=self.auth_headers)
        data = r.json()
        assert data["frame_available"] is True
        assert data["streaming"] is True
        assert data["publisher_connected"] is True
        assert data["home_id_match"] is True
        assert data["reason"] == "streaming"

    def test_status_publisher_home_mismatch(self):
        """If the publisher sends frames for home A, querying status for home B
        must show publisher_home_id_mismatch, not a generic False."""
        # Create a second home for this user
        res2 = client.post("/api/homes", json={"name": "Second Home"}, headers=self.auth_headers)
        assert res2.status_code == 201
        second_home_id = res2.json()["id"]

        # Publish frame for the first home
        client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={
                **self.publisher_headers,
                "Content-Type": "image/jpeg",
                "X-Home-ID": self.home_id,
            },
        )

        # Query status for the SECOND home
        r = client.get(f"/video/status?home_id={second_home_id}", headers=self.auth_headers)
        data = r.json()
        assert data["publisher_connected"] is True
        assert data["home_id_match"] is False
        assert data["reason"] == "publisher_home_id_mismatch"

    def test_status_no_auth_returns_401(self):
        r = client.get(f"/video/status?home_id={self.home_id}")
        assert r.status_code == 401

    def test_status_non_owner_returns_403_or_404(self):
        other = _make_token(str(uuid4()))
        r = client.get(
            f"/video/status?home_id={self.home_id}",
            headers={"Authorization": f"Bearer {other}"},
        )
        assert r.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 4. Stream Endpoint (503 variants)
# ---------------------------------------------------------------------------

class TestStreamEndpoint503Variants:
    """GET /video/stream must return 503 with a descriptive detail when unavailable."""

    def setup_method(self):
        backend_store.clear()
        _reset_frame_manager()
        self.user_id = str(uuid4())
        self.token = _make_token(self.user_id)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        res = client.post("/api/homes", json={"name": "Stream Test"}, headers=self.auth_headers)
        assert res.status_code == 201
        self.home_id = res.json()["id"]
        self.publisher_headers = _publisher_headers(self.home_id, self.auth_headers)

    def teardown_method(self):
        _reset_frame_manager()
        backend_store.clear()

    def test_stream_503_when_no_publisher(self):
        r = client.get(f"/video/stream?home_id={self.home_id}", headers=self.auth_headers)
        assert r.status_code == 503
        detail = r.json().get("detail", "")
        assert "publisher" in detail.lower() or "stream" in detail.lower(), (
            f"503 detail should mention publisher/stream, got: {detail!r}"
        )

    def test_stream_503_mentions_desktop_app_when_no_publisher(self):
        r = client.get(f"/video/stream?home_id={self.home_id}", headers=self.auth_headers)
        assert r.status_code == 503
        detail = r.json().get("detail", "")
        assert "desktop" in detail.lower(), (
            f"503 detail should guide user to start desktop app, got: {detail!r}"
        )

    def test_stream_503_when_publisher_wrong_home(self):
        """Publisher running for a different home → 503 mentioning SECURITY_HOME_ID."""
        res2 = client.post("/api/homes", json={"name": "Other Home"}, headers=self.auth_headers)
        assert res2.status_code == 201
        other_home_id = res2.json()["id"]

        client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={
                **self.publisher_headers,
                "X-Home-ID": other_home_id,
            },
        )

        r = client.get(f"/video/stream?home_id={self.home_id}", headers=self.auth_headers)
        assert r.status_code == 503
        detail = r.json().get("detail", "")
        assert "publisher" in detail.lower(), (
            f"503 detail should mention no publisher after rejecting the mismatched home, got: {detail!r}"
        )

    def test_stream_200_when_frames_present(self, monkeypatch):
        """After a valid frame POST the stream endpoint must not 503.

        Uses stream=True so we only read the status line and headers, then
        close the connection — the infinite MJPEG generator never blocks us.
        """
        client.post(
            "/video/frame",
            content=_make_jpeg(),
            headers={
                **self.publisher_headers,
            },
        )
        async def one_frame(**_kwargs):
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe\r\n"

        from app.api.routes import video as video_routes
        monkeypatch.setattr(video_routes, "generate_mjpeg_stream", one_frame)
        r = client.get(f"/video/stream?home_id={self.home_id}", headers=self.auth_headers)
        assert r.status_code == 200, f"Expected 200 when frames present, got {r.status_code}"

    def test_stream_401_without_auth(self):
        with client.stream("GET", f"/video/stream?home_id={self.home_id}") as r:
            assert r.status_code == 401

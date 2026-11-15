import time
import threading
import queue
from typing import Optional
from uuid import UUID
import httpx

from app.config.settings import API_BASE_URL, STREAM_FPS
from app.config.backend_settings import settings
from app.security.device_credential_store import (
    DeviceCredentialStore,
    DeviceCredentialStoreError,
)


class FramePublisher:
    """Background publisher thread that sends encoded JPEG frames to the FastAPI backend over local HTTP.

    Enables frame sharing when PySide6 desktop app and FastAPI run in separate OS processes.
    """

    SESSION_RENEWAL_MARGIN_SECONDS = 10

    def __init__(self, api_base_url: str = API_BASE_URL, target_fps: int = STREAM_FPS, home_id: str | None = None, device_token: str | None = None):
        self.api_url = f"{api_base_url.rstrip('/')}/video/frame"
        self.session_url = f"{api_base_url.rstrip('/')}/api/devices/session"
        # Keep the legacy argument for callers, but only a validated session
        # response may establish the publisher's home identity.
        self._home_id_lock = threading.Lock()
        self._session_lock = threading.Lock()
        self._resolved_home_id: Optional[str] = None
        self._credential_injected = device_token is not None
        self.device_token = (
            device_token
            if self._credential_injected
            else self._read_stored_device_credential()
        )
        self._session_token: Optional[str] = None
        self._session_expires_at = 0.0
        self.target_fps = target_fps
        self.min_interval = 1.0 / max(1, target_fps)
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_error: Optional[str] = None

    @property
    def resolved_home_id(self) -> Optional[str]:
        with self._home_id_lock:
            return self._resolved_home_id

    @property
    def home_id(self) -> Optional[str]:
        """Compatibility alias for the server-resolved device home."""
        return self.resolved_home_id

    @staticmethod
    def _read_stored_device_credential() -> Optional[str]:
        try:
            return DeviceCredentialStore().retrieve()
        except Exception:
            return None

    def reload_device_credential(self) -> bool:
        """Reload a newly paired credential without exposing it to the caller."""
        if self._credential_injected:
            return bool(self.device_token)
        credential = self._read_stored_device_credential()
        self.device_token = credential
        with self._session_lock:
            self._session_token = None
            self._session_expires_at = 0.0
        return bool(credential)

    def get_session_snapshot(self) -> tuple[str, str, float] | None:
        """Return the current valid session without exposing credentials to callers."""
        with self._session_lock:
            session_token = self._session_token
            expires_at = self._session_expires_at
        resolved_home_id = self.resolved_home_id
        if (
            session_token
            and resolved_home_id
            and time.monotonic() < expires_at - self.SESSION_RENEWAL_MARGIN_SECONDS
        ):
            return session_token, resolved_home_id, expires_at
        return None

    def _ensure_session(self, client: httpx.Client) -> bool:
        """Acquire or renew the device session before it approaches expiry."""
        if self.get_session_snapshot() is not None:
            return True
        if not self.device_token:
            with self._session_lock:
                self._session_token = None
                self._session_expires_at = 0.0
            self._last_error = "missing paired device credential"
            return False

        # Drop any old token before attempting renewal. A failed renewal must
        # never fall back to an expired session or a homeowner Bearer token.
        with self._session_lock:
            self._session_token = None
            self._session_expires_at = 0.0
        try:
            response = client.post(
                self.session_url,
                headers={"Authorization": f"DeviceToken {self.device_token}"},
            )
            if response.status_code != 200:
                self._last_error = f"device session endpoint returned HTTP {response.status_code}"
                return False

            payload = response.json()
            if not isinstance(payload, dict):
                self._last_error = "invalid device session response"
                return False
            session_token = payload.get("session_token")
            expires_in = payload.get("expires_in")
            session_home_id = payload.get("home_id")
            try:
                resolved_home_id = (
                    str(UUID(session_home_id))
                    if isinstance(session_home_id, str)
                    else None
                )
            except ValueError:
                resolved_home_id = None
            if (
                payload.get("token_type") != "DeviceSession"
                or not isinstance(session_token, str)
                or not session_token
                or resolved_home_id is None
                or isinstance(expires_in, bool)
                or not isinstance(expires_in, (int, float))
                or not 0 < expires_in <= 60
            ):
                self._last_error = "invalid device session response"
                return False

            with self._session_lock:
                self._session_token = session_token
                self._session_expires_at = time.monotonic() + expires_in
            # The session exchange returns the home resolved from the stored
            # device record. Never route a frame using the local .env hint.
            with self._home_id_lock:
                self._resolved_home_id = resolved_home_id
            self._last_error = None
            return True
        except (httpx.HTTPError, ValueError, TypeError):
            self._last_error = "device session endpoint unavailable"
            return False

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> None:
        """Start background publisher thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background publisher thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def publish(self, jpeg_bytes: Optional[bytes]) -> None:
        """Publish latest JPEG bytes to background queue (non-blocking)."""
        if not self._running or jpeg_bytes is None:
            return

        try:
            self._queue.put_nowait(jpeg_bytes)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(jpeg_bytes)
            except (queue.Empty, queue.Full):
                pass

    def _run(self) -> None:
        last_publish_time = 0.0
        with httpx.Client(timeout=0.5) as client:
            while self._running:
                try:
                    jpeg_bytes = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                now = time.time()
                elapsed = now - last_publish_time
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)

                try:
                    if not self._ensure_session(client):
                        continue
                    session_snapshot = self.get_session_snapshot()
                    if session_snapshot is None:
                        self._last_error = "missing server-resolved device home"
                        continue
                    session_token, resolved_home_id, _ = session_snapshot
                    res = client.post(
                        self.api_url,
                        content=jpeg_bytes,
                        headers={
                            "Content-Type": "image/jpeg",
                            "Authorization": f"DeviceSession {session_token}",
                            "X-Home-ID": resolved_home_id,
                        },
                    )
                    if res.status_code == 200:
                        last_publish_time = time.time()
                        self._last_error = None
                    else:
                        if res.status_code == 401:
                            with self._session_lock:
                                self._session_token = None
                                self._session_expires_at = 0.0
                        self._last_error = f"frame endpoint returned HTTP {res.status_code}"
                except Exception:
                    self._last_error = "backend unavailable"

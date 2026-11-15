from __future__ import annotations

from datetime import datetime, timezone
import math
import queue
import threading
import time
from typing import Callable

import httpx

from app.config.settings import (
    API_BASE_URL,
    FACEOCC_MAX_RESULT_AGE_SECONDS,
)
from app.security.face_occlusion_runtime import FaceOcclusionDiagnostic


_STATUS_VALUES = {"success", "unavailable", "invalid", "failed", "no_face", "stale"}
_SAFE_REASONS = {
    "",
    "segmentation_completed",
    "no_face_detected",
    "model_unavailable",
    "model_file_missing",
    "invalid_face_crop",
    "poor_quality",
    "diagnostic_result_expired",
    "unsupported_crop_mode",
    "landmarks_unavailable_for_alignment",
    "invalid_landmarks",
    "landmarks_outside_crop",
    "landmarks_nearly_duplicate",
    "landmarks_degenerate",
    "alignment_transform_failed",
    "inference_failed",
}


def _safe_reason(reason: object) -> str:
    value = str(reason or "")
    if value in _SAFE_REASONS:
        return value
    # Unknown reasons are deliberately collapsed; exception bodies and paths
    # must never become API-facing diagnostic data.
    return "diagnostic_status"


class FaceOcclusionDiagnosticPublisher:
    """Bounded, diagnostic-only publisher using FramePublisher's session."""

    def __init__(
        self,
        session_provider: Callable[[], tuple[str, str, float] | None],
        *,
        api_base_url: str = API_BASE_URL,
        max_age_seconds: float = FACEOCC_MAX_RESULT_AGE_SECONDS,
        max_retries: int = 2,
        backoff_seconds: float = 0.1,
        http_client_factory: Callable[[], httpx.Client] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_age_seconds <= 0 or max_retries < 0 or backoff_seconds < 0:
            raise ValueError("invalid FaceOcc publisher configuration")
        self.endpoint = f"{api_base_url.rstrip('/')}/api/video/face-occlusion"
        self.max_age_seconds = max_age_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._session_provider = session_provider
        self._http_client_factory = http_client_factory
        self._clock = clock
        self._queue: queue.Queue[FaceOcclusionDiagnostic] = queue.Queue(maxsize=1)
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_error: str | None = None
        self._queue_replacements = 0
        self._dropped_expired = 0
        self._retry_count = 0
        self._published_count = 0
        self._lock = threading.Lock()

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    @property
    def queue_replacements(self) -> int:
        with self._lock:
            return self._queue_replacements

    @property
    def dropped_expired(self) -> int:
        with self._lock:
            return self._dropped_expired

    @property
    def retry_count(self) -> int:
        with self._lock:
            return self._retry_count

    @property
    def published_count(self) -> int:
        with self._lock:
            return self._published_count

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name="faceocc-diagnostic-publisher",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._running = False
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.0, timeout))
        self._thread = None

    def submit(self, diagnostic: FaceOcclusionDiagnostic) -> bool:
        """Queue only safe metadata; never blocks the camera/inference thread."""
        if not self._running or not self._is_publishable(diagnostic):
            return False
        try:
            self._queue.put_nowait(diagnostic)
            return True
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(diagnostic)
                with self._lock:
                    self._queue_replacements += 1
                return True
            except (queue.Empty, queue.Full):
                return False

    def _is_publishable(self, diagnostic: FaceOcclusionDiagnostic) -> bool:
        if diagnostic.status not in _STATUS_VALUES or diagnostic.status == "stale":
            return False
        completed_at = diagnostic.completed_at
        if completed_at is None:
            return False
        try:
            age = self._clock() - float(completed_at)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(age) or age < 0 or age > self.max_age_seconds:
            with self._lock:
                self._dropped_expired += 1
            return False
        return diagnostic.frame_sequence >= 0 and diagnostic.face_index >= -1

    @staticmethod
    def _payload(diagnostic: FaceOcclusionDiagnostic) -> dict:
        result = diagnostic.result
        visible_ratio = getattr(result, "visible_ratio", None)
        inference_ms = getattr(result, "inference_ms", None)
        if visible_ratio is not None:
            visible_ratio = float(visible_ratio)
            if not math.isfinite(visible_ratio) or not 0 <= visible_ratio <= 1:
                visible_ratio = None
        if inference_ms is not None:
            inference_ms = float(inference_ms)
            if not math.isfinite(inference_ms) or not 0 <= inference_ms <= 60000:
                inference_ms = None
        return {
            "face_index": diagnostic.face_index,
            "frame_sequence": diagnostic.frame_sequence,
            "status": diagnostic.status,
            "visible_ratio": visible_ratio,
            "inference_ms": inference_ms,
            "result_timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": _safe_reason(diagnostic.reason),
        }

    def _run(self) -> None:
        client_factory = self._http_client_factory or (lambda: httpx.Client(timeout=1.0))
        with client_factory() as client:
            while self._running:
                try:
                    diagnostic = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                self._publish_one(client, diagnostic)

    def _publish_one(self, client: httpx.Client, diagnostic: FaceOcclusionDiagnostic) -> None:
        session = None
        for attempt in range(self.max_retries + 1):
            session = self._session_provider()
            if session is not None:
                break
            if attempt < self.max_retries:
                self._backoff(attempt)
        if session is None:
            self._set_error("device session unavailable")
            return

        session_token, home_id, _ = session
        payload = self._payload(diagnostic)
        headers = {
            "Authorization": f"DeviceSession {session_token}",
            "X-Home-ID": home_id,
            "Content-Type": "application/json",
        }
        for attempt in range(self.max_retries + 1):
            try:
                response = client.post(self.endpoint, json={"home_id": home_id, **payload}, headers=headers)
                if response.status_code in {200, 201}:
                    with self._lock:
                        self._published_count += 1
                        self._last_error = None
                    return
                if response.status_code in {401, 403, 409} or response.status_code < 500:
                    self._set_error(f"diagnostic endpoint returned HTTP {response.status_code}")
                    return
            except httpx.HTTPError:
                pass
            if attempt < self.max_retries:
                with self._lock:
                    self._retry_count += 1
                self._backoff(attempt)
        self._set_error("diagnostic endpoint unavailable")

    def _backoff(self, attempt: int) -> None:
        time.sleep(self.backoff_seconds * (2**attempt))

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

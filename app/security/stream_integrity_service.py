"""Lightweight, conservative health checks for frames received from a camera.

Image-only checks cannot prove that a static room is frozen or that a sequence is
maliciously replayed. Accordingly, this service emits a replay *suspicion* only
for a repeating multi-frame sequence and exposes identical frames as ambiguous.
"""

from collections import deque
from datetime import datetime, timezone
import time
from typing import Any

import cv2
import numpy as np
from app.config.settings import CAMERA_OBSTRUCTION_DARKNESS, CAMERA_OBSTRUCTION_SHARPNESS


class StreamIntegrityService:
    def __init__(
        self,
        stale_after_seconds: float = 3.0,
        repeated_sequence_length: int = 4,
        replay_repeats: int = 3,
        scene_change_distance: int = 48,
    ) -> None:
        self.stale_after_seconds = stale_after_seconds
        self.repeated_sequence_length = max(2, repeated_sequence_length)
        self.replay_repeats = max(2, replay_repeats)
        self.scene_change_distance = scene_change_distance
        self._hashes: deque[int] = deque(maxlen=self.repeated_sequence_length * self.replay_repeats * 2)
        self._last_frame_time: float | None = None
        self._last_hash: int | None = None
        self._identical_count = 0
        self._dark_or_blurred_since: float | None = None
        self._last_scene_change_at: float | None = None

    @staticmethod
    def _dhash(frame: np.ndarray) -> int:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        bits = small[:, 1:] > small[:, :-1]
        value = 0
        for bit in bits.flatten():
            value = (value << 1) | int(bit)
        return value

    @staticmethod
    def _distance(left: int, right: int) -> int:
        return (left ^ right).bit_count()

    def _repeating_sequence(self) -> bool:
        length = self.repeated_sequence_length
        required = length * self.replay_repeats
        hashes = list(self._hashes)
        if len(hashes) < required:
            return False
        sample = hashes[-required:]
        # Period-one frames are ambiguous with a static room; only repeated
        # patterns with at least two distinct adjacent frames qualify.
        if len(set(sample[:length])) < 2:
            return False
        return all(sample[i] == sample[i % length] for i in range(required))

    def inspect(
        self,
        frame: np.ndarray | None,
        *,
        captured_at: float | None = None,
        now: float | None = None,
        read_ok: bool = True,
        camera_open: bool = True,
    ) -> list[dict[str, Any]]:
        now = time.monotonic() if now is None else now
        captured_at = now if captured_at is None else captured_at
        events: list[dict[str, Any]] = []

        def event(kind: str, confidence: float, reason: str) -> None:
            events.append({
                "event_type": kind,
                "confidence": confidence,
                "reason": reason,
                "observed_at": datetime.now(timezone.utc).isoformat(),
            })

        if not camera_open:
            event("camera_offline", 1.0, "Camera device is not open.")
            self.reset()
            return events
        if not read_ok or frame is None:
            event("camera_read_failure", 1.0, "Camera did not return a valid frame.")
            return events
        if (
            not isinstance(frame, np.ndarray)
            or frame.size == 0
            or frame.ndim not in (2, 3)
            or (frame.ndim == 3 and frame.shape[2] not in (3, 4))
        ):
            event("invalid_camera_frame", 1.0, "Camera returned an empty or malformed frame.")
            return events
        if now - captured_at > self.stale_after_seconds:
            event("stream_stale", 0.95, "Frame capture timestamp exceeded the configured freshness limit.")

        current_hash = self._dhash(frame)
        if self._last_hash is not None:
            distance = self._distance(self._last_hash, current_hash)
            if distance == 0:
                self._identical_count += 1
            else:
                self._identical_count = 0
            if distance >= self.scene_change_distance and (
                self._last_scene_change_at is None or now - self._last_scene_change_at > 5.0
            ):
                event("scene_change_suspected", 0.55, "Large perceptual change from the previous sampled frame.")
                self._last_scene_change_at = now
        self._last_hash = current_hash
        self._hashes.append(current_hash)

        if self._repeating_sequence():
            event("replay_suspected", 0.65, "A multi-frame perceptual-hash sequence repeated; this is not proof of malicious replay.")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        brightness = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if brightness < CAMERA_OBSTRUCTION_DARKNESS or sharpness < CAMERA_OBSTRUCTION_SHARPNESS:
            self._dark_or_blurred_since = self._dark_or_blurred_since or now
            if now - self._dark_or_blurred_since >= 3.0:
                event("possible_camera_obstruction", 0.4, "Image is persistently very dark or low-detail; darkness and static scenes can be legitimate.")
                self._dark_or_blurred_since = now
        else:
            self._dark_or_blurred_since = None

        self._last_frame_time = captured_at
        return events

    @property
    def identical_frame_count(self) -> int:
        """Exposed as an ambiguous diagnostic; never equated with a freeze by itself."""
        return self._identical_count

    def reset(self) -> None:
        self._hashes.clear()
        self._last_frame_time = None
        self._last_hash = None
        self._identical_count = 0
        self._dark_or_blurred_since = None
        self._last_scene_change_at = None

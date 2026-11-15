"""Asynchronous, diagnostic-only FaceOcc runtime."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path
import threading
import time
import math
from typing import Any, Callable

import cv2
import numpy as np

from app.security.face_occlusion_service import FaceOcclusionResult, FaceOcclusionService
from app.config.settings import (
    FACEOCC_MAX_RESULT_AGE_SECONDS,
    get_faceocc_model_path,
)


DEFAULT_FACEOCC_MODEL_PATH = Path(get_faceocc_model_path())
MIN_CROP_SIZE = 16

STATUS_QUEUED = "queued"
STATUS_REPLACED = "replaced_pending"
STATUS_NOT_SAMPLED = "not_sampled"
STATUS_NO_FACE = "no_face"
STATUS_NOT_RUNNING = "not_running"
STATUS_STOPPED = "stopped"
STATUS_SUCCESS = "success"
STATUS_UNAVAILABLE = "unavailable"
STATUS_INVALID = "invalid"
STATUS_FAILED = "failed"
STATUS_STALE = "stale"


@dataclass(frozen=True)
class FaceOcclusionCrop:
    face_index: int
    box: tuple[int, int, int, int]
    crop: np.ndarray | None
    landmarks: np.ndarray | None


@dataclass(frozen=True)
class FaceOcclusionJob:
    frame_sequence: int
    submitted_at: float | None
    faces: tuple[FaceOcclusionCrop, ...]
    mode: str


@dataclass(frozen=True)
class FaceOcclusionDiagnostic:
    frame_sequence: int
    face_index: int
    box: tuple[int, int, int, int]
    submitted_at: float
    completed_at: float | None
    status: str
    reason: str
    result: FaceOcclusionResult | None = None


class FaceOcclusionRuntime:
    """Run FaceOcc jobs on one private worker thread.

    The queue stores at most one pending frame batch. Results are keyed by the
    original frame sequence and face index; they are never matched by position
    in a later detection list.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        sample_interval_frames: int = 15,
        max_result_age_seconds: float = FACEOCC_MAX_RESULT_AGE_SECONDS,
        service_factory: Callable[[str | Path], FaceOcclusionService] = FaceOcclusionService,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if sample_interval_frames < 1:
            raise ValueError("sample_interval_frames must be at least 1")
        if max_result_age_seconds <= 0:
            raise ValueError("max_result_age_seconds must be positive")
        self.model_path = Path(
            get_faceocc_model_path() if model_path is None else model_path
        )
        self.sample_interval_frames = sample_interval_frames
        self.max_result_age_seconds = float(max_result_age_seconds)
        self._service_factory = service_factory
        self._clock = clock
        self._condition = threading.Condition()
        self._pending: FaceOcclusionJob | None = None
        self._results: deque[FaceOcclusionDiagnostic] = deque(maxlen=128)
        self._thread: threading.Thread | None = None
        self._stop_requested = False
        self._service: FaceOcclusionService | None = None
        self._service_error: str | None = None
        self._latest_submitted_frame = -1
        self._latest_result: FaceOcclusionDiagnostic | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def latest_result(self) -> FaceOcclusionDiagnostic | None:
        with self._condition:
            return self._latest_result

    @property
    def max_result_age_frames(self) -> int:
        return self.sample_interval_frames * 2

    def start(self) -> None:
        with self._condition:
            if self.is_running:
                return
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._run,
                name="faceocc-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        with self._condition:
            self._stop_requested = True
            self._pending = None
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, timeout))
        with self._condition:
            if thread is not None and not thread.is_alive():
                self._thread = None

    def submit_faces(
        self,
        frame: np.ndarray | None,
        frame_sequence: int,
        detected_faces: list[dict[str, Any]],
        *,
        mode: str = "direct_crop",
    ) -> str:
        """Copy a detected face batch and enqueue it without blocking inference."""
        if frame_sequence % self.sample_interval_frames != 0:
            return STATUS_NOT_SAMPLED
        if not detected_faces:
            if self.is_running:
                self._append_status(
                    frame_sequence,
                    STATUS_NO_FACE,
                    "no_face_detected",
                )
            return STATUS_NO_FACE
        if not self.is_running:
            return STATUS_NOT_RUNNING
        if frame is None or not isinstance(frame, np.ndarray) or frame.ndim != 3:
            return STATUS_INVALID

        faces = tuple(
            self._copy_face(frame, index, face_info, mode)
            for index, face_info in enumerate(detected_faces)
        )
        job = FaceOcclusionJob(
            frame_sequence=frame_sequence,
            submitted_at=self._clock(),
            faces=faces,
            mode=mode,
        )
        with self._condition:
            if self._stop_requested:
                return STATUS_STOPPED
            if frame_sequence < self._latest_submitted_frame:
                return "dropped_old"
            replaced = self._pending is not None
            self._pending = job
            self._latest_submitted_frame = frame_sequence
            self._condition.notify()
            return STATUS_REPLACED if replaced else STATUS_QUEUED

    def get_results(
        self,
        *,
        frame_sequence: int | None = None,
        face_index: int | None = None,
        current_frame_sequence: int | None = None,
        max_age_frames: int | None = None,
        max_age_seconds: float | None = None,
    ) -> list[FaceOcclusionDiagnostic]:
        with self._condition:
            results = list(self._results)
        filtered = [
            result
            for result in results
            if (frame_sequence is None or result.frame_sequence == frame_sequence)
            and (face_index is None or result.face_index == face_index)
            and not self.is_stale(
                result,
                current_frame_sequence=current_frame_sequence,
                max_age_frames=max_age_frames,
                max_age_seconds=max_age_seconds,
            )
        ]
        return filtered

    def get_result(
        self,
        frame_sequence: int,
        face_index: int,
        *,
        current_frame_sequence: int | None = None,
        max_age_frames: int | None = None,
        max_age_seconds: float | None = None,
    ) -> FaceOcclusionDiagnostic | None:
        results = self.get_results(
            frame_sequence=frame_sequence,
            face_index=face_index,
            current_frame_sequence=current_frame_sequence,
            max_age_frames=max_age_frames,
            max_age_seconds=max_age_seconds,
        )
        return results[-1] if results else None

    def drain_results(self) -> list[FaceOcclusionDiagnostic]:
        with self._condition:
            results = list(self._results)
            self._results.clear()
        return results

    @staticmethod
    def mark_stale(result: FaceOcclusionDiagnostic) -> FaceOcclusionDiagnostic:
        return replace(
            result,
            status=STATUS_STALE,
            reason="diagnostic_result_expired",
        )

    def is_stale(
        self,
        result: FaceOcclusionDiagnostic,
        *,
        current_frame_sequence: int | None = None,
        max_age_frames: int | None = None,
        max_age_seconds: float | None = None,
        now: float | None = None,
    ) -> bool:
        if (
            current_frame_sequence is not None
            and max_age_frames is not None
            and current_frame_sequence - result.frame_sequence > max_age_frames
        ):
            return True
        if max_age_seconds is not None:
            current_time = self._clock() if now is None else now
            try:
                completed_at = float(result.completed_at)
                current_time = float(current_time)
            except (TypeError, ValueError):
                return True
            if not math.isfinite(completed_at) or not math.isfinite(current_time):
                return True
            if current_time - completed_at > max_age_seconds:
                return True
        return False

    def _copy_face(
        self,
        frame: np.ndarray,
        face_index: int,
        face_info: dict[str, Any],
        mode: str,
    ) -> FaceOcclusionCrop:
        raw_box = face_info.get("box", (0, 0, 0, 0))
        try:
            x, y, width, height = (int(value) for value in raw_box)
        except (TypeError, ValueError):
            x, y, width, height = 0, 0, 0, 0
        frame_height, frame_width = frame.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(frame_width, x + width), min(frame_height, y + height)
        crop = frame[y0:y1, x0:x1].copy() if x1 > x0 and y1 > y0 else None
        if crop is not None and (
            crop.shape[0] < MIN_CROP_SIZE or crop.shape[1] < MIN_CROP_SIZE
        ):
            crop = None

        landmarks = None
        if mode == "landmark_aligned" and face_info.get("raw") is not None:
            try:
                landmarks = np.asarray(face_info["raw"][4:14], dtype=np.float32).reshape(5, 2)
                landmarks -= np.array([x0, y0], dtype=np.float32)
            except (TypeError, ValueError):
                landmarks = None

        return FaceOcclusionCrop(
            face_index=face_index,
            box=(x, y, width, height),
            crop=crop,
            landmarks=landmarks,
        )

    def _run(self) -> None:
        try:
            try:
                self._service = self._service_factory(self.model_path)
                if getattr(self._service, "net", object()) is None:
                    self._service_error = getattr(
                        self._service,
                        "load_error",
                        None,
                    ) or "model_unavailable"
            except Exception as exc:
                self._service_error = f"model_initialization_failed: {type(exc).__name__}"
            if self._service_error is not None:
                self._append_status(
                    -1,
                    STATUS_UNAVAILABLE,
                    self._service_error,
                )

            while True:
                with self._condition:
                    while self._pending is None and not self._stop_requested:
                        self._condition.wait()
                    if self._stop_requested and self._pending is None:
                        return
                    job = self._pending
                    self._pending = None
                if job is not None:
                    self._process_job(job)
        finally:
            with self._condition:
                self._thread = None

    def _process_job(self, job: FaceOcclusionJob) -> None:
        for face in job.faces:
            started_at = self._clock()
            if self._service_error is not None or self._service is None:
                self._append_result(
                    job,
                    face,
                    STATUS_UNAVAILABLE,
                    self._service_error or "model_unavailable",
                    None,
                    started_at,
                )
                continue
            if face.crop is None:
                self._append_result(
                    job,
                    face,
                    STATUS_INVALID,
                    "invalid_face_crop",
                    None,
                    started_at,
                )
                continue
            try:
                result = self._service.evaluate(
                    face.crop,
                    mode=job.mode,
                    landmarks=face.landmarks,
                )
                status, reason = self._map_result(result)
            except Exception as exc:
                result = None
                status = STATUS_FAILED
                reason = f"inference_exception: {type(exc).__name__}"
            self._append_result(job, face, status, reason, result, started_at)

    @staticmethod
    def _map_result(result: FaceOcclusionResult) -> tuple[str, str]:
        if result.state == "segmentation_available":
            return STATUS_SUCCESS, result.reason
        if result.state == "model_unavailable":
            return STATUS_UNAVAILABLE, result.reason
        if result.state in {"invalid_input", "not_evaluated", "poor_quality", "face_not_detected"}:
            return STATUS_INVALID, result.reason
        return STATUS_FAILED, result.reason

    def _append_result(
        self,
        job: FaceOcclusionJob,
        face: FaceOcclusionCrop,
        status: str,
        reason: str,
        result: FaceOcclusionResult | None,
        started_at: float,
    ) -> None:
        completed_at = self._clock()
        diagnostic = FaceOcclusionDiagnostic(
            frame_sequence=job.frame_sequence,
            face_index=face.face_index,
            box=face.box,
            submitted_at=job.submitted_at,
            completed_at=completed_at,
            status=status,
            reason=reason,
            result=result,
        )
        with self._condition:
            self._results.append(diagnostic)
            self._latest_result = diagnostic

    def _append_status(
        self,
        frame_sequence: int,
        status: str,
        reason: str,
    ) -> None:
        now = self._clock()
        diagnostic = FaceOcclusionDiagnostic(
            frame_sequence=frame_sequence,
            face_index=-1,
            box=(0, 0, 0, 0),
            submitted_at=now,
            completed_at=now,
            status=status,
            reason=reason,
            result=None,
        )
        with self._condition:
            self._results.append(diagnostic)
            self._latest_result = diagnostic

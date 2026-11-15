"""Diagnostic-only FaceOcc visible-face segmentation service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import time

import cv2
import numpy as np


IMAGE_SIZE = (256, 256)
IMAGE_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGE_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
MASK_THRESHOLD = 0.5
MIN_CROP_SIZE = 16
MIN_LANDMARK_SEPARATION_PX = 1.0
VALID_MODES = {"direct_crop", "landmark_aligned"}

# Standard five-point face template scaled from the 112px ArcFace layout.
# This is an experimental alignment convention, not the SFace alignment path.
_ALIGNMENT_TEMPLATE = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
) * (256.0 / 112.0)


@dataclass
class FaceOcclusionResult:
    state: str
    reason: str
    mode: str
    output_dimensions: tuple[int, ...] | None = None
    logits: np.ndarray | None = None
    probability_map: np.ndarray | None = None
    binary_mask: np.ndarray | None = None
    visible_ratio: float | None = None
    mean_probability: float | None = None
    near_threshold_fraction: float | None = None
    inference_ms: float | None = None


class FaceOcclusionService:
    """Run the standalone FaceOcc ONNX model on a supplied BGR face crop.

    This service does not detect faces, access a camera, alter recognition, or
    make security decisions. Landmark coordinates, when supplied, are five
    points relative to the supplied crop in the order expected by YuNet.
    """

    def __init__(self, model_path: str | Path, *, near_threshold_band: float = 0.05) -> None:
        self.model_path = Path(model_path)
        self.near_threshold_band = float(near_threshold_band)
        self.net: cv2.dnn_Net | None = None
        self.load_error: str | None = None

        if not self.model_path.is_file():
            self.load_error = "model_file_missing"
            return
        try:
            self.net = cv2.dnn.readNetFromONNX(str(self.model_path))
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except Exception as exc:
            self.load_error = f"model_load_failed: {type(exc).__name__}"

    def evaluate(
        self,
        crop: np.ndarray | None,
        *,
        mode: str = "direct_crop",
        landmarks: np.ndarray | list[list[float]] | None = None,
        quality: dict[str, Any] | None = None,
        face_detected: bool | None = None,
    ) -> FaceOcclusionResult:
        """Evaluate one BGR face crop without running face detection."""
        if mode not in VALID_MODES:
            return self._failure("invalid_input", "unsupported_crop_mode", mode)
        if self.net is None:
            return self._failure("model_unavailable", self.load_error or "model_unavailable", mode)
        if face_detected is False:
            return self._failure("face_not_detected", "caller_reported_no_face", mode)
        if quality and quality.get("quality") == "uncertain":
            return self._failure("poor_quality", str(quality.get("reason", "quality_uncertain")), mode)
        if crop is None:
            return self._failure("not_evaluated", "crop_not_supplied", mode)

        valid, reason = self._validate_crop(crop)
        if not valid:
            return self._failure("invalid_input", reason, mode)

        prepared_crop = crop
        if mode == "landmark_aligned":
            prepared_crop, reason = self._align_crop(crop, landmarks)
            if prepared_crop is None:
                return self._failure("uncertain", reason, mode)

        try:
            blob = self._preprocess(prepared_crop)
            if blob.shape != (1, 3, 256, 256):
                return self._failure("inference_failed", "invalid_preprocessed_shape", mode)
            self.net.setInput(blob)
            started = time.perf_counter()
            output = self.net.forward()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
        except Exception as exc:
            return self._failure("inference_failed", f"inference_error: {type(exc).__name__}", mode)

        if output is None or tuple(output.shape) != (1, 1, 256, 256):
            shape = None if output is None else tuple(output.shape)
            return self._failure("inference_failed", f"unexpected_output_shape: {shape}", mode)
        if not np.all(np.isfinite(output)):
            return self._failure("inference_failed", "non_finite_output", mode)

        logits = output.astype(np.float32, copy=False)
        probabilities = self._sigmoid(logits)
        binary_mask = (probabilities >= MASK_THRESHOLD).astype(np.uint8)
        near_threshold = np.abs(probabilities - MASK_THRESHOLD) <= self.near_threshold_band

        return FaceOcclusionResult(
            state="segmentation_available",
            reason="segmentation_completed",
            mode=mode,
            output_dimensions=tuple(output.shape),
            logits=logits.copy(),
            probability_map=probabilities.copy(),
            binary_mask=binary_mask.copy(),
            visible_ratio=float(binary_mask.mean()),
            mean_probability=float(probabilities.mean()),
            near_threshold_fraction=float(near_threshold.mean()),
            inference_ms=elapsed_ms,
        )

    @staticmethod
    def _validate_crop(crop: np.ndarray | None) -> tuple[bool, str]:
        if not isinstance(crop, np.ndarray):
            return False, "crop_is_not_numpy_array"
        if crop.size == 0:
            return False, "empty_crop"
        if crop.ndim != 3 or crop.shape[2] != 3:
            return False, "expected_bgr_three_channel_image"
        if crop.shape[0] < MIN_CROP_SIZE or crop.shape[1] < MIN_CROP_SIZE:
            return False, "crop_too_small"
        if not np.all(np.isfinite(crop)):
            return False, "crop_contains_non_finite_values"
        return True, "valid_crop"

    @staticmethod
    def _preprocess(crop: np.ndarray) -> np.ndarray:
        # Pillow is not a project dependency; INTER_LINEAR is the documented
        # deterministic fallback for the Phase 5.1 bilinear resize.
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, IMAGE_SIZE, interpolation=cv2.INTER_LINEAR)
        values = resized.astype(np.float32) / 255.0
        values = (values - IMAGE_MEAN) / IMAGE_STD
        return np.transpose(values, (2, 0, 1))[None, ...].astype(np.float32)

    @staticmethod
    def _sigmoid(logits: np.ndarray) -> np.ndarray:
        probabilities = np.empty_like(logits, dtype=np.float32)
        positive = logits >= 0
        probabilities[positive] = 1.0 / (1.0 + np.exp(-logits[positive]))
        negative_exp = np.exp(logits[~positive])
        probabilities[~positive] = negative_exp / (1.0 + negative_exp)
        return probabilities

    @staticmethod
    def _align_crop(crop: np.ndarray, landmarks: Any) -> tuple[np.ndarray | None, str]:
        if landmarks is None:
            return None, "landmarks_unavailable_for_alignment"
        try:
            raw_points = np.asarray(landmarks)
        except (TypeError, ValueError):
            return None, "invalid_landmarks"
        if not np.issubdtype(raw_points.dtype, np.number) or raw_points.shape != (5, 2):
            return None, "invalid_landmarks"
        points = raw_points.astype(np.float32, copy=False)
        if not np.all(np.isfinite(points)):
            return None, "invalid_landmarks"
        height, width = crop.shape[:2]
        if np.any(points[:, 0] < 0) or np.any(points[:, 0] >= width):
            return None, "landmarks_outside_crop"
        if np.any(points[:, 1] < 0) or np.any(points[:, 1] >= height):
            return None, "landmarks_outside_crop"
        distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
        distinct_distances = distances[np.triu_indices(5, k=1)]
        if np.any(distinct_distances < MIN_LANDMARK_SEPARATION_PX):
            return None, "landmarks_nearly_duplicate"
        hull = cv2.convexHull(points.reshape(-1, 1, 2))
        hull_area = cv2.contourArea(hull)
        area_epsilon = np.finfo(np.float32).eps * max(width, height) ** 2
        if hull_area <= area_epsilon:
            return None, "landmarks_degenerate"
        transform, _ = cv2.estimateAffinePartial2D(points, _ALIGNMENT_TEMPLATE, method=cv2.LMEDS)
        if transform is None or not np.all(np.isfinite(transform)):
            return None, "alignment_transform_failed"
        if abs(float(np.linalg.det(transform[:, :2]))) <= np.finfo(np.float32).eps:
            return None, "alignment_transform_failed"
        aligned = cv2.warpAffine(crop, transform, IMAGE_SIZE, flags=cv2.INTER_LINEAR)
        if aligned.size == 0:
            return None, "aligned_crop_empty"
        return aligned, "aligned_crop_created"

    @staticmethod
    def _failure(state: str, reason: str, mode: str) -> FaceOcclusionResult:
        return FaceOcclusionResult(state=state, reason=reason, mode=mode)

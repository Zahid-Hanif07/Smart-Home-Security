from datetime import datetime, timezone
from math import isfinite
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


FaceOcclusionStatus = Literal[
    "success",
    "unavailable",
    "invalid",
    "failed",
    "no_face",
    "stale",
]
FaceOcclusionReason = Literal[
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
    "diagnostic_status",
]
FaceOcclusionFreshness = Literal["fresh", "stale"]


class FaceOcclusionDiagnosticCreate(BaseModel):
    """Minimal device-published FaceOcc diagnostic; no image data is accepted."""

    home_id: UUID
    face_index: int = Field(ge=-1)
    frame_sequence: int = Field(ge=0)
    status: FaceOcclusionStatus
    visible_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    inference_ms: float | None = Field(default=None, ge=0.0, le=60000.0)
    result_timestamp: datetime
    reason: FaceOcclusionReason = Field(default="", max_length=120)

    model_config = ConfigDict(extra="forbid")

    @field_validator("visible_ratio", "inference_ms")
    @classmethod
    def reject_non_finite_numbers(cls, value):
        if value is not None and not isfinite(value):
            raise ValueError("numeric diagnostic values must be finite")
        return value

    @field_validator("result_timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("result_timestamp must include a timezone")
        return value.astimezone(timezone.utc)


class FaceOcclusionDiagnosticResponse(BaseModel):
    home_id: UUID
    device_id: UUID
    face_index: int
    frame_sequence: int
    status: FaceOcclusionStatus
    visible_ratio: float | None = None
    inference_ms: float | None = None
    result_timestamp: datetime
    freshness: FaceOcclusionFreshness
    reason: FaceOcclusionReason


class FaceOcclusionStatusResponse(BaseModel):
    home_id: UUID
    results: list[FaceOcclusionDiagnosticResponse]

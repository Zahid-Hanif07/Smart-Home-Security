from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import UUID

from app.config.settings import FACEOCC_MAX_RESULT_AGE_SECONDS
from app.models.face_occlusion_diagnostic import (
    FaceOcclusionDiagnosticCreate,
    FaceOcclusionDiagnosticResponse,
    FaceOcclusionStatusResponse,
)


class OlderFaceOcclusionResultError(ValueError):
    pass


class FaceOcclusionDiagnosticStore:
    """Bounded latest-result state; data is lost when the backend restarts."""

    def __init__(self, max_age_seconds: float = FACEOCC_MAX_RESULT_AGE_SECONDS):
        self.max_age_seconds = max_age_seconds
        self._lock = Lock()
        self._latest: dict[tuple[UUID, int], FaceOcclusionDiagnosticResponse] = {}

    def put(
        self,
        device_id: UUID,
        diagnostic: FaceOcclusionDiagnosticCreate,
    ) -> FaceOcclusionDiagnosticResponse:
        key = (diagnostic.home_id, diagnostic.face_index)
        with self._lock:
            current = self._latest.get(key)
            if current and (
                diagnostic.result_timestamp < current.result_timestamp
                or (
                    diagnostic.result_timestamp == current.result_timestamp
                    and diagnostic.frame_sequence <= current.frame_sequence
                )
            ):
                raise OlderFaceOcclusionResultError
            response = FaceOcclusionDiagnosticResponse(
                **diagnostic.model_dump(),
                device_id=device_id,
                freshness="fresh",
            )
            self._latest[key] = response
            return response

    def get_home(self, home_id: UUID) -> FaceOcclusionStatusResponse:
        now = datetime.now(timezone.utc)
        with self._lock:
            records = [
                self._with_freshness(item, now)
                for (stored_home_id, _), item in self._latest.items()
                if stored_home_id == home_id
            ]
        records.sort(key=lambda item: item.face_index)
        return FaceOcclusionStatusResponse(home_id=home_id, results=records)

    def clear(self) -> None:
        with self._lock:
            self._latest.clear()

    def _with_freshness(self, item, now: datetime):
        age_seconds = (now - item.result_timestamp).total_seconds()
        freshness = (
            "fresh"
            if item.status != "stale" and 0 <= age_seconds <= self.max_age_seconds
            else "stale"
        )
        return item.model_copy(update={"freshness": freshness})


face_occlusion_diagnostic_store = FaceOcclusionDiagnosticStore()

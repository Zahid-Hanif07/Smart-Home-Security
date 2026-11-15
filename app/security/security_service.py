from typing import Any, Optional
from app.security.motion_detection_service import MotionDetectionService
from app.security.face_detection_service import FaceDetectionService
from app.security.face_recognition_service import FaceRecognitionService
from app.security.security_event_service import SecurityEventService
from app.security.stream_integrity_service import StreamIntegrityService
from app.config.settings import (
    FACE_PROCESS_EVERY_N_FRAMES,
    STREAM_STALE_AFTER_SECONDS,
    STREAM_REPEATED_SEQUENCE_LENGTH,
    STREAM_REPLAY_REPEATS,
    STREAM_SCENE_CHANGE_DISTANCE,
)

_UNSET_HOME_ID = object()


class SecurityService:
    """Security service coordinator.

    Coordinates motion detection, face detection, face embedding, identity recognition,
    and debounced backend event reporting.
    """

    def __init__(
        self,
        home_id: Any = _UNSET_HOME_ID,
        face_process_every_n_frames: int = FACE_PROCESS_EVERY_N_FRAMES,
        face_occlusion_runtime=None,
    ):
        self.motion_service = MotionDetectionService()
        self.face_service = FaceDetectionService()
        if home_id is _UNSET_HOME_ID:
            self.recognition_service = FaceRecognitionService()
            self.event_service = SecurityEventService()
        else:
            self.recognition_service = FaceRecognitionService(home_id=home_id)
            self.event_service = SecurityEventService(home_id=home_id)
        self.integrity_service = StreamIntegrityService(
            stale_after_seconds=STREAM_STALE_AFTER_SECONDS,
            repeated_sequence_length=STREAM_REPEATED_SEQUENCE_LENGTH,
            replay_repeats=STREAM_REPLAY_REPEATS,
            scene_change_distance=STREAM_SCENE_CHANGE_DISTANCE,
        )
        self.face_process_every_n_frames = max(1, face_process_every_n_frames)
        self._frame_index = 0
        self._last_faces = []
        self._last_recognition_results = []
        self.face_occlusion_runtime = face_occlusion_runtime

    def set_face_occlusion_runtime(self, runtime) -> None:
        """Attach an optional diagnostic runtime without changing recognition."""
        self.face_occlusion_runtime = runtime

    @property
    def frame_sequence(self) -> int:
        return self._frame_index

    def set_home_id(self, home_id: Optional[str]) -> None:
        """Update backend home ID for security event reporting and recognition reload."""
        self.event_service.set_home_id(home_id)
        self.recognition_service.home_id = home_id
        self.recognition_service.reload_database(home_id=home_id)
        self._last_faces = []
        self._last_recognition_results = []
        self._frame_index = self.face_process_every_n_frames - 1

    def process_frame(self, frame):
        """Process video frame through active security modules."""
        annotated_frame, _, _, _, _ = self.process_security_frame(frame)
        return annotated_frame

    def process_security_frame(self, frame):
        """Process video frame and return annotated frame along with detection details.

        Pipeline Architecture:
        1. Camera Frame -> MotionDetectionService
        2. If Motion Detected -> FaceDetectionService
        3. If Face(s) Detected -> FaceRecognitionService (Embedding & Matching)
        4. Annotate frame with motion bounding box and face/identity banner
        5. Pass results to SecurityEventService for debounced backend reporting

        Returns:
            tuple: (annotated_frame, motion_detected, face_detected, face_count, recognition_results)
        """
        annotated_frame, motion_detected, _ = self.motion_service.process_frame(frame)
        self._frame_index += 1
        if self._frame_index % self.face_process_every_n_frames == 0:
            # Face checks are independent of motion: a person can be stationary
            # after entering the scene. Sampling limits model cost on CPU.
            self._last_faces = self.face_service.detect_faces(frame)
            if self.face_occlusion_runtime is not None:
                try:
                    self.face_occlusion_runtime.submit_faces(
                        frame,
                        self._frame_index,
                        self._last_faces,
                    )
                except Exception as exc:
                    print(f"Non-fatal FaceOcc diagnostic error: {exc}")
            self._last_recognition_results = (
                self.recognition_service.recognize_faces(frame, self._last_faces)
                if self._last_faces else []
            )

        detected_faces = self._last_faces
        recognition_results = self._last_recognition_results
        if detected_faces:
            annotated_frame = self.face_service.draw_faces(annotated_frame, recognition_results)

        face_detected = len(detected_faces) > 0

        # Non-blocking backend event reporting
        try:
            self.event_service.process_recognition_results(
                motion_detected=motion_detected,
                recognition_results=recognition_results,
                frame=frame,
            )
            for system_event in self.integrity_service.inspect(frame):
                self.event_service.handle_system_event(system_event, frame=frame)
        except Exception as e:
            print(f"Non-fatal error in security event service: {e}")

        return (
            annotated_frame,
            motion_detected,
            face_detected,
            len(detected_faces),
            recognition_results,
        )

    def reload_face_database(self) -> None:
        """Reload face embeddings from database after new registration."""
        self.recognition_service.reload_database()

    def get_status(self) -> str:
        """Return operational status of the security module."""
        count = len(self.recognition_service.registered_people)
        source = self.recognition_service.data_source
        return f"Security modules active; {count} face identities loaded from {source}; liveness unverified."

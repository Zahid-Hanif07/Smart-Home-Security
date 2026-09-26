from typing import Optional
from app.security.motion_detection_service import MotionDetectionService
from app.security.face_detection_service import FaceDetectionService
from app.security.face_recognition_service import FaceRecognitionService
from app.security.security_event_service import SecurityEventService


class SecurityService:
    """Security service coordinator.

    Coordinates motion detection, face detection, face embedding, identity recognition,
    and debounced backend event reporting.
    """

    def __init__(self, home_id: Optional[str] = None):
        self.motion_service = MotionDetectionService()
        self.face_service = FaceDetectionService()
        self.recognition_service = FaceRecognitionService()
        self.event_service = SecurityEventService(home_id=home_id)

    def set_home_id(self, home_id: Optional[str]) -> None:
        """Update backend home ID for security event reporting."""
        self.event_service.set_home_id(home_id)

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
        annotated_frame, motion_detected, motion_score = self.motion_service.process_frame(frame)
        detected_faces = []
        recognition_results = []

        if motion_detected:
            detected_faces = self.face_service.detect_faces(frame)
            if detected_faces:
                # Perform identity recognition for each detected face
                recognition_results = self.recognition_service.recognize_faces(
                    frame, detected_faces
                )
                # Draw faces with identity labels on the annotated frame
                annotated_frame = self.face_service.draw_faces(
                    annotated_frame, recognition_results
                )

        face_detected = len(detected_faces) > 0

        # Non-blocking backend event reporting
        try:
            self.event_service.process_recognition_results(
                motion_detected=motion_detected,
                recognition_results=recognition_results,
            )
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
        names = self.recognition_service.database.get_registered_names()
        count = len(names)
        return f"Smart Home Security initialized with Motion, Face Detection, Identity Recognition ({count} registered person(s)), and Backend Reporting."

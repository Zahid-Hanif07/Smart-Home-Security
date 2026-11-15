import unittest
import numpy as np
import cv2
from unittest.mock import Mock
from app.security.motion_detection_service import MotionDetectionService
from app.security.face_detection_service import FaceDetectionService
from app.security.security_service import SecurityService


class TestFaceDetection(unittest.TestCase):

    def setUp(self):
        self.security_service = SecurityService(face_process_every_n_frames=1)
        self.face_service = FaceDetectionService()

    def test_face_detection_runs_even_without_motion(self):
        """Faces are sampled on a schedule independent of motion detection."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detector = Mock(return_value=[])
        self.security_service.face_service.detect_faces = detector
        self.security_service.recognition_service.recognize_faces = Mock(return_value=[])
        self.security_service.event_service.process_recognition_results = Mock()

        self.security_service.process_security_frame(frame)
        self.security_service.process_security_frame(frame)
        self.assertEqual(detector.call_count, 2)

    def test_face_detection_service_initialization(self):
        """Verify FaceDetectionService initializes YuNet ONNX model correctly."""
        self.assertIsNotNone(self.face_service.detector)

    def test_empty_frame_face_detection(self):
        """Verify empty black frame produces zero face detections."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        faces = self.face_service.detect_faces(frame)
        self.assertEqual(len(faces), 0)

    def test_drawing_bounding_boxes(self):
        """Verify drawing method places labels and bounding boxes without error."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_faces = [{"box": (100, 100, 50, 50), "confidence": 0.95}]
        annotated = self.face_service.draw_faces(frame, dummy_faces)
        self.assertEqual(annotated.shape, (480, 640, 3))


if __name__ == "__main__":
    unittest.main()

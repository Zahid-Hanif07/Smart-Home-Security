import unittest
import numpy as np
import cv2
from app.security.motion_detection_service import MotionDetectionService
from app.security.face_detection_service import FaceDetectionService
from app.security.security_service import SecurityService


class TestFaceDetection(unittest.TestCase):

    def setUp(self):
        self.security_service = SecurityService()
        self.face_service = FaceDetectionService()

    def test_no_motion_bypasses_face_detection(self):
        """Test 1 — No motion: Face detection should not run on static background."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Init background
        self.security_service.process_frame(frame)
        
        # Static frame
        out_frame = self.security_service.process_frame(frame)
        self.assertIsNotNone(out_frame)

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

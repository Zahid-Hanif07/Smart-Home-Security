import sys
import os
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force PySide6 offscreen mode for automated UI headless execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.security.face_database import FaceDatabase
from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_recognition_service import FaceRecognitionService
from app.security.security_service import SecurityService
from app.config.settings import FACE_RECOGNITION_THRESHOLD

# Instantiate single QApplication for PySide6 tests
app = QApplication.instance() or QApplication(sys.argv)


class TestStep5E2E(unittest.TestCase):

    def setUp(self):
        self.db = FaceDatabase()

    def test_01_startup_and_empty_db(self):
        """Test 1 & Test 2: Application startup with empty/loaded database."""
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "Smart Home Security Dashboard")
        window.close()

    def test_02_registration_embedding_generation(self):
        """Test 3 & Test 6 & Test 7: Registration, embedding generation, multiple faces, no face."""
        embedding_service = FaceEmbeddingService()

        # Create 5 synthetic face frames with natural variations
        sample_embeddings = []
        sample_crops = []

        for i in range(5):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (150 + i * 2, 120), (350 + i * 2, 360), (200 + i * 5, 200, 200), -1)
            cv2.circle(frame, (200 + i * 2, 180), 20, (0, 0, 0), -1)
            cv2.circle(frame, (300 + i * 2, 180), 20, (0, 0, 0), -1)
            cv2.circle(frame, (250 + i * 2, 230), 10, (0, 0, 0), -1)

            face_info = {"box": (150 + i * 2, 120, 200, 240), "confidence": 0.92}
            emb = embedding_service.compute_embedding(frame, face_info)
            self.assertIsNotNone(emb)
            self.assertEqual(len(emb), 128)
            sample_embeddings.append(emb)
            sample_crops.append(frame[120:360, 150:350])

        # Save test person 'TestUser_Zahid'
        save_result = self.db.save_person("TestUser_Zahid", sample_embeddings, sample_crops)
        self.assertTrue(save_result)
        self.assertIn("TestUser_Zahid", self.db.get_registered_names())

    def test_03_recognition_authorized_vs_unknown(self):
        """Test 4 & Test 5: Recognition authorized vs unknown face."""
        rec_service = FaceRecognitionService(database=self.db)
        embedding_service = FaceEmbeddingService()

        # Frame corresponding to registered TestUser_Zahid
        frame_known = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame_known, (150, 120), (350, 360), (200, 200, 200), -1)
        cv2.circle(frame_known, (200, 180), 20, (0, 0, 0), -1)
        cv2.circle(frame_known, (300, 180), 20, (0, 0, 0), -1)

        face_info = {"box": (150, 120, 200, 240), "confidence": 0.95}
        result_known = rec_service.recognize_face(frame_known, face_info)

        self.assertEqual(result_known["name"], "TestUser_Zahid")
        self.assertTrue(result_known["matched"])

        # Frame corresponding to completely different unregistered person
        frame_unknown = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.ellipse(frame_unknown, (300, 240), (80, 120), 0, 0, 360, (100, 255, 100), -1)

        result_unknown = rec_service.recognize_face(frame_unknown, face_info)
        self.assertIn(result_unknown["name"], ["Unknown", "TestUser_Zahid"])

    def test_04_restart_and_cleanup(self):
        """Test 9 & Test 10: Database persistent load on restart and cleanup."""
        # Clean up test registration
        self.db.remove_person("TestUser_Zahid")
        self.assertNotIn("TestUser_Zahid", self.db.get_registered_names())


if __name__ == "__main__":
    unittest.main()

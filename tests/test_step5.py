import sys
import os
import unittest
import numpy as np
import cv2

# Add root project path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_database import FaceDatabase
from app.security.face_recognition_service import FaceRecognitionService
from app.security.security_service import SecurityService
from app.config.settings import FACE_RECOGNITION_THRESHOLD


class TestStep5FaceRecognition(unittest.TestCase):

    def setUp(self):
        self.test_db_file = "data/face_database/test_embeddings.json"
        self.test_db_dir = "data/face_database"
        self.test_faces_dir = "data/test_faces"
        self.db = FaceDatabase(
            db_file=self.test_db_file,
            db_dir=self.test_db_dir,
            faces_dir=self.test_faces_dir,
        )

    def tearDown(self):
        # Cleanup test database files
        if os.path.exists(self.test_db_file):
            os.remove(self.test_db_file)
        if os.path.exists(self.test_faces_dir):
            import shutil
            shutil.rmtree(self.test_faces_dir, ignore_errors=True)

    def test_01_embedding_service(self):
        """Test FaceEmbeddingService initialization and fallback embedding calculation."""
        service = FaceEmbeddingService()
        self.assertIsNotNone(service.recognizer)

        # Create dummy frame and face info dict
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(dummy_frame, (100, 100), (300, 300), (255, 255, 255), -1)

        face_info = {"box": (100, 100, 200, 200), "confidence": 0.95}
        emb = service.compute_embedding(dummy_frame, face_info)

        self.assertIsNotNone(emb)
        self.assertEqual(len(emb), 128)
        self.assertEqual(emb.dtype, np.float32)

    def test_02_face_database_crud(self):
        """Test local face database saving, loading, and deletion."""
        dummy_emb1 = np.random.rand(128).astype(np.float32)
        dummy_emb2 = np.random.rand(128).astype(np.float32)
        dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)

        # 1. Save person 'Zahid'
        save_success = self.db.save_person(
            name="Zahid",
            embeddings=[dummy_emb1, dummy_emb2],
            face_images=[dummy_crop],
        )
        self.assertTrue(save_success)
        self.assertTrue(os.path.exists(self.test_db_file))

        # 2. Load database
        loaded = self.db.load_database()
        self.assertIn("Zahid", loaded)
        self.assertEqual(len(loaded["Zahid"]), 2)
        self.assertEqual(len(loaded["Zahid"][0]), 128)

        # 3. Remove person
        self.db.remove_person("Zahid")
        loaded_after = self.db.load_database()
        self.assertNotIn("Zahid", loaded_after)

    def test_03_recognition_service(self):
        """Test FaceRecognitionService identity matching and empty database handling."""
        emb_service = FaceEmbeddingService()
        rec_service = FaceRecognitionService(
            embedding_service=emb_service,
            database=self.db,
            threshold=FACE_RECOGNITION_THRESHOLD,
        )

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(dummy_frame, (100, 100), (300, 300), (255, 255, 255), -1)
        face_info = {"box": (100, 100, 200, 200), "confidence": 0.9}

        # 1. Empty DB -> Returns Unknown
        result_empty = rec_service.recognize_face(dummy_frame, face_info)
        self.assertEqual(result_empty["name"], "Unknown")
        self.assertFalse(result_empty["matched"])

        # 2. Register sample embedding generated from this exact face
        emb = emb_service.compute_embedding(dummy_frame, face_info)
        self.assertIsNotNone(emb)
        self.db.save_person("Amish", [emb])
        rec_service.reload_database()

        # 3. Recognize exact face -> Should match 'Amish'
        result_matched = rec_service.recognize_face(dummy_frame, face_info)
        self.assertEqual(result_matched["name"], "Amish")
        self.assertTrue(result_matched["matched"])
        self.assertGreaterEqual(result_matched["similarity"], FACE_RECOGNITION_THRESHOLD)

    def test_04_security_service_pipeline(self):
        """Test complete SecurityService processing pipeline."""
        sec_service = SecurityService()
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        annotated_frame, motion, face, face_count, rec_results = (
            sec_service.process_security_frame(dummy_frame)
        )
        self.assertIsNotNone(annotated_frame)
        self.assertIsInstance(motion, bool)
        self.assertIsInstance(face, bool)
        self.assertIsInstance(rec_results, list)


if __name__ == "__main__":
    unittest.main()

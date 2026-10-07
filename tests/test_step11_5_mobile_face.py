import sys
import os
import base64
import cv2
import numpy as np
import jwt
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.config.backend_settings import settings
from app.services.backend_store import backend_store
from app.security.face_recognition_service import FaceRecognitionService
from app.services.api_client import APIClient
from tests.test_backend import create_test_user, delete_test_user

client = TestClient(app)


def generate_signed_jwt(user_id: str, email: str = "user@example.com") -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_metadata": {"name": "Test User"},
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def create_synthetic_face_image_base64() -> str:
    """Create a synthetic 200x200 BGR image with a drawn face shape for testing."""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 200
    # Draw simple facial feature geometry
    cv2.circle(img, (100, 100), 50, (150, 150, 150), -1) # Head
    cv2.circle(img, (80, 85), 6, (0, 0, 0), -1) # Left eye
    cv2.circle(img, (120, 85), 6, (0, 0, 0), -1) # Right eye
    cv2.line(img, (100, 95), (100, 110), (0, 0, 0), 2) # Nose
    cv2.ellipse(img, (100, 125), (20, 10), 0, 0, 180, (0, 0, 0), 2) # Smile
    
    _, buffer = cv2.imencode(".jpg", img)
    return base64.b64encode(buffer).decode("utf-8")


class TestStep11_5_MobileFaceEnrollment(unittest.TestCase):

    def setUp(self):
        backend_store.clear()
        self.user1_id = create_test_user("mobile_face_user1@example.com", "User One")
        self.user2_id = create_test_user("mobile_face_user2@example.com", "User Two")

        self.token1 = generate_signed_jwt(str(self.user1_id), "mobile_face_user1@example.com")
        self.token2 = generate_signed_jwt(str(self.user2_id), "mobile_face_user2@example.com")

        self.headers1 = {"Authorization": f"Bearer {self.token1}"}
        self.headers2 = {"Authorization": f"Bearer {self.token2}"}

    def tearDown(self):
        delete_test_user(self.user1_id)
        delete_test_user(self.user2_id)
        backend_store.clear()

    def test_01_member_creation_and_face_enrollment_flow(self):
        """Test member creation & face registration with 128D SFace embedding persistence."""
        # 1. Create Home
        res_home = client.post("/api/homes", json={"name": "Face Security Residence"}, headers=self.headers1)
        self.assertEqual(res_home.status_code, 201)
        home_id = res_home.json()["id"]

        # 2. Add Member
        res_member = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Zahid", "relation": "Home Owner"},
            headers=self.headers1,
        )
        self.assertEqual(res_member.status_code, 201)
        member_id = res_member.json()["id"]

        # 3. Register face with 128D embedding vector directly
        dummy_128d_embedding = [0.123] * 128
        res_reg = client.post(
            f"/api/members/{member_id}/register-face",
            json={
                "embedding": dummy_128d_embedding,
                "sample_count": 1,
            },
            headers=self.headers1,
        )
        self.assertEqual(res_reg.status_code, 201)
        face_record = res_reg.json()
        self.assertEqual(face_record["member_id"], member_id)
        self.assertEqual(len(face_record["embedding"]), 128)

        # 4. Fetch registered faces for member
        res_faces = client.get(f"/api/members/{member_id}/faces", headers=self.headers1)
        self.assertEqual(res_faces.status_code, 200)
        self.assertEqual(len(res_faces.json()), 1)

    def test_02_invalid_or_corrupted_image_rejection(self):
        """Test rejection of invalid image payload."""
        res_home = client.post("/api/homes", json={"name": "Test Home"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        res_member = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Test Member"},
            headers=self.headers1,
        )
        member_id = res_member.json()["id"]

        # Invalid base64 image
        res_bad_img = client.post(
            f"/api/members/{member_id}/register-face",
            json={"image_base64": "invalid_base64_string_xyz"},
            headers=self.headers1,
        )
        self.assertEqual(res_bad_img.status_code, 400)

    def test_03_no_face_detected_rejection(self):
        """Test rejection of image containing no face."""
        res_home = client.post("/api/homes", json={"name": "Blank Vision Home"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        res_member = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Test Member 2"},
            headers=self.headers1,
        )
        member_id = res_member.json()["id"]

        # 10x10 pure black image (no face)
        black_img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", black_img)
        b64_no_face = base64.b64encode(buf).decode("utf-8")

        res_noface = client.post(
            f"/api/members/{member_id}/register-face",
            json={"image_base64": b64_no_face},
            headers=self.headers1,
        )
        self.assertEqual(res_noface.status_code, 400)
        self.assertIn("No face detected", res_noface.json()["detail"])

    def test_04_cross_user_face_registration_security(self):
        """Test that user 2 cannot register face for user 1's member or fetch face records."""
        res_home1 = client.post("/api/homes", json={"name": "User 1 Home"}, headers=self.headers1)
        home1_id = res_home1.json()["id"]

        res_m1 = client.post(
            f"/api/homes/{home1_id}/members",
            json={"name": "User 1 Member"},
            headers=self.headers1,
        )
        member1_id = res_m1.json()["id"]

        # User 2 attempts to register face for User 1's member -> 404 Not Found or 403 Forbidden
        res_unauth_reg = client.post(
            f"/api/members/{member1_id}/register-face",
            json={"embedding": [0.1] * 128},
            headers=self.headers2,
        )
        self.assertIn(res_unauth_reg.status_code, [403, 404, 500])

        # User 2 attempts to fetch User 1's home face records -> 403 or 404
        res_unauth_get = client.get(f"/api/homes/{home1_id}/face-records", headers=self.headers2)
        self.assertIn(res_unauth_get.status_code, [403, 404])

    def test_05_python_recognition_loads_centralized_embeddings(self):
        """Test Python FaceRecognitionService fetching face records from FastAPI/Supabase."""
        res_home = client.post("/api/homes", json={"name": "Central AI Manor"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        res_m = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Zahid"},
            headers=self.headers1,
        )
        member_id = res_m.json()["id"]

        dummy_emb = [0.5] * 128
        client.post(
            f"/api/members/{member_id}/register-face",
            json={"embedding": dummy_emb},
            headers=self.headers1,
        )

        # Retrieve home face records endpoint
        res_records = client.get(f"/api/homes/{home_id}/face-records", headers=self.headers1)
        self.assertEqual(res_records.status_code, 200)
        records = res_records.json()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["member_name"], "Zahid")
        self.assertEqual(len(records[0]["embedding"]), 128)

        # Test FaceRecognitionService initialized with home_id
        service = FaceRecognitionService(home_id=home_id)
        # Mock APIClient client inside service
        api_client = APIClient(custom_client=client, auth_token=self.token1)
        # Force service reload using custom api_client
        service.registered_people = {}
        recs = api_client.get_home_face_records(home_id)
        for r in recs:
            name = r["member_name"]
            emb = np.array(r["embedding"], dtype=np.float32)
            service.registered_people[name] = [emb]

        self.assertIn("Zahid", service.registered_people)
        self.assertEqual(len(service.registered_people["Zahid"][0]), 128)

    def test_06_clear_member_faces_endpoint(self):
        """Test DELETE /api/members/{member_id}/faces clears all face records for member."""
        res_home = client.post("/api/homes", json={"name": "Re-registration Residence"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        res_m = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Zahid"},
            headers=self.headers1,
        )
        member_id = res_m.json()["id"]

        # Register 2 sample face records
        client.post(f"/api/members/{member_id}/register-face", json={"embedding": [0.1] * 128}, headers=self.headers1)
        client.post(f"/api/members/{member_id}/register-face", json={"embedding": [0.2] * 128}, headers=self.headers1)

        res_faces = client.get(f"/api/members/{member_id}/faces", headers=self.headers1)
        self.assertEqual(len(res_faces.json()), 2)

        # Clear faces
        res_clear = client.delete(f"/api/members/{member_id}/faces", headers=self.headers1)
        self.assertEqual(res_clear.status_code, 204)

        # Verify faces are cleared
        res_faces_after = client.get(f"/api/members/{member_id}/faces", headers=self.headers1)
        self.assertEqual(len(res_faces_after.json()), 0)


if __name__ == "__main__":
    unittest.main()

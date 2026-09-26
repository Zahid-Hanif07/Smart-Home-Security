import sys
import os
import jwt
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.config.backend_settings import settings
from app.services.backend_store import backend_store

client = TestClient(app)


def generate_test_token(user_id: str, email: str = "testuser@example.com") -> str:
    """Generate signed JWT token for automated testing."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_metadata": {"name": "Test User"},
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


class TestBackendAPI(unittest.TestCase):

    def setUp(self):
        backend_store.clear()
        self.user_id = uuid4()
        self.token = generate_test_token(str(self.user_id), "zahid@example.com")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_01_health_and_root(self):
        """Test 1: Health check & root endpoints."""
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        response_root = client.get("/")
        self.assertEqual(response_root.status_code, 200)
        self.assertIn("status", response_root.json())

    def test_02_authentication_jwt(self):
        """Test 2: JWT Authentication verification and unauthorized access."""
        # Missing token
        res_no_token = client.get("/api/auth/me")
        self.assertEqual(res_no_token.status_code, 401)

        # Invalid token
        res_bad_token = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(res_bad_token.status_code, 401)

        # Valid token
        res_valid = client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.json()
        self.assertEqual(data["id"], str(self.user_id))
        self.assertEqual(data["email"], "zahid@example.com")

    def test_03_home_crud(self):
        """Test 3: Home creation and retrieval."""
        # Create home
        home_payload = {"name": "Zahid Villa", "address": "123 Security Ave"}
        res_create = client.post("/api/homes", json=home_payload, headers=self.headers)
        self.assertEqual(res_create.status_code, 201)
        home_data = res_create.json()
        self.assertEqual(home_data["name"], "Zahid Villa")
        self.assertEqual(home_data["owner_id"], str(self.user_id))
        home_id = home_data["id"]

        # Retrieve user homes
        res_list = client.get("/api/homes", headers=self.headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)

        # Retrieve single home
        res_get = client.get(f"/api/homes/{home_id}", headers=self.headers)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], home_id)

    def test_04_member_and_face_crud(self):
        """Test 4: Member creation and face record metadata storage."""
        # Create Home
        res_home = client.post("/api/homes", json={"name": "Family House"}, headers=self.headers)
        home_id = res_home.json()["id"]

        # Create Home Member
        member_payload = {"name": "Amish", "relation": "Brother"}
        res_member = client.post(f"/api/homes/{home_id}/members", json=member_payload, headers=self.headers)
        self.assertEqual(res_member.status_code, 201)
        member_data = res_member.json()
        member_id = member_data["id"]
        self.assertEqual(member_data["name"], "Amish")

        # Create Face Record for Member
        face_payload = {
            "image_path": "data/faces/Amish/sample_01.jpg",
            "embedding": [0.1, -0.2, 0.3],
            "sample_count": 5,
        }
        res_face = client.post(f"/api/members/{member_id}/faces", json=face_payload, headers=self.headers)
        self.assertEqual(res_face.status_code, 201)
        face_data = res_face.json()
        self.assertEqual(face_data["member_id"], member_id)

        # Get Member Face Records
        res_faces = client.get(f"/api/members/{member_id}/faces", headers=self.headers)
        self.assertEqual(res_faces.status_code, 200)
        self.assertEqual(len(res_faces.json()), 1)

    def test_05_devices_logs_alerts(self):
        """Test 5: Device, Security Log, and Alert management."""
        # Create Home
        res_home = client.post("/api/homes", json={"name": "Smart Hub"}, headers=self.headers)
        home_id = res_home.json()["id"]

        # Create Device
        dev_payload = {"device_name": "Front Camera", "device_type": "camera", "status": "online"}
        res_dev = client.post(f"/api/homes/{home_id}/devices", json=dev_payload, headers=self.headers)
        self.assertEqual(res_dev.status_code, 201)

        # Create Security Log
        log_payload = {
            "event_type": "motion_detected",
            "description": "Motion observed at front door",
            "is_authorized": True,
        }
        res_log = client.post(f"/api/homes/{home_id}/security-logs", json=log_payload, headers=self.headers)
        self.assertEqual(res_log.status_code, 201)

        # Filter Security Logs by event_type
        res_filter_logs = client.get(f"/api/homes/{home_id}/security-logs?event_type=motion_detected", headers=self.headers)
        self.assertEqual(res_filter_logs.status_code, 200)
        self.assertEqual(len(res_filter_logs.json()), 1)

        # Create Alert
        alert_payload = {
            "alert_type": "unknown_person",
            "title": "Unknown Person Detected",
            "message": "Unregistered person at entrance.",
        }
        res_alert = client.post(f"/api/homes/{home_id}/alerts", json=alert_payload, headers=self.headers)
        self.assertEqual(res_alert.status_code, 201)
        alert_id = res_alert.json()["id"]

        # Mark Alert as Read
        res_read = client.put(f"/api/alerts/{alert_id}/read", json={"is_read": True}, headers=self.headers)
        self.assertEqual(res_read.status_code, 200)
        self.assertTrue(res_read.json()["is_read"])


if __name__ == "__main__":
    unittest.main()

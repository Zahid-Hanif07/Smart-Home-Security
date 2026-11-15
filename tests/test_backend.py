import sys
import os
import time
import jwt
import unittest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

# Ensure isolated test mode by default to prevent unintentional live Supabase calls
if os.getenv("RUN_LIVE_SUPABASE_TESTS") != "1":
    os.environ["TEST_ISOLATED_MODE"] = "1"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.config.backend_settings import settings
from app.services.backend_store import backend_store
from app.repositories.home_repository import is_supabase_configured
from app.database.supabase_client import SupabaseClientManager

client = TestClient(app)


def create_test_user(email: str = "testuser@example.com", name: str = "Test User") -> UUID:
    """Create a test user. If live Supabase testing is explicitly requested and configured,
    create a real Supabase Auth user. Otherwise return a synthetic UUID for isolated testing."""
    if is_supabase_configured() and os.getenv("RUN_LIVE_SUPABASE_TESTS") == "1":
        admin_client = SupabaseClientManager.get_admin_client()
        if admin_client:
            unique_email = f"test_{uuid4().hex[:8]}_{email}"
            try:
                user_res = admin_client.auth.admin.create_user({
                    "email": unique_email,
                    "password": "TestPassword123!",
                    "email_confirm": True,
                    "user_metadata": {"name": name},
                })
                return UUID(user_res.user.id)
            except Exception as e:
                print(f"[TEST WARNING] Failed to create Supabase Auth test user: {e}")
    return uuid4()


def delete_test_user(user_id: UUID) -> None:
    """Clean up test user if running in live Supabase test mode."""
    if is_supabase_configured() and os.getenv("RUN_LIVE_SUPABASE_TESTS") == "1":
        admin_client = SupabaseClientManager.get_admin_client()
        if admin_client:
            try:
                admin_client.auth.admin.delete_user(str(user_id))
            except Exception:
                pass


def generate_test_token(user_id: str, email: str = "testuser@example.com", expires_in: int = 3600) -> str:
    """Generate signed JWT token for automated testing."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_metadata": {"name": "Test User"},
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


class TestBackendAPI(unittest.TestCase):

    def setUp(self):
        backend_store.clear()
        self.user_id = create_test_user("zahid@example.com", "Test User")
        self.token = generate_test_token(str(self.user_id), "zahid@example.com")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        delete_test_user(self.user_id)
        backend_store.clear()

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

    def test_06_expired_and_tampered_token_rejection(self):
        """Test 6: Expired and tampered tokens are rejected with HTTP 401."""
        expired_token = generate_test_token(str(self.user_id), "zahid@example.com", expires_in=-120)
        res_exp = client.get("/api/homes", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res_exp.status_code, 401)

        tampered_token = jwt.encode(
            {"sub": str(self.user_id), "email": "zahid@example.com"},
            "wrong_signature_secret",
            algorithm="HS256",
        )
        res_tampered = client.get("/api/homes", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(res_tampered.status_code, 401)

    def test_07_empty_home_id_rejection(self):
        """Test 7: Empty or missing home ID parameter is rejected before processing."""
        res_empty = client.post("/api/homes//members", json={"name": "Alice"}, headers=self.headers)
        self.assertEqual(res_empty.status_code, 400)

        res_empty_get = client.get("/api/homes//members", headers=self.headers)
        self.assertEqual(res_empty_get.status_code, 400)

    def test_08_cross_user_isolation(self):
        """Test 8: User cannot view or mutate another user's home."""
        user_b_id = uuid4()
        token_b = generate_test_token(str(user_b_id), "other@example.com")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A creates a home
        res_home_a = client.post("/api/homes", json={"name": "Home A"}, headers=self.headers)
        self.assertEqual(res_home_a.status_code, 201)
        home_a_id = res_home_a.json()["id"]

        # User B should NOT see Home A in their homes list
        res_b_list = client.get("/api/homes", headers=headers_b)
        self.assertEqual(res_b_list.status_code, 200)
        self.assertEqual(len(res_b_list.json()), 0)

        # User B cannot access Home A directly
        res_b_get = client.get(f"/api/homes/{home_a_id}", headers=headers_b)
        self.assertIn(res_b_get.status_code, (403, 404))

    def test_09_profile_persistence_and_update(self):
        """Test 9: User profile creation and updates persist."""
        res_update = client.post("/api/auth/profile", json={"name": "Zahid Updated"}, headers=self.headers)
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["name"], "Zahid Updated")

        res_me = client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.json()["name"], "Zahid Updated")

    def test_10_unauthenticated_requests_do_not_return_empty_lists(self):
        """Test 10: Unauthenticated requests return 401 instead of falsely empty collections."""
        res_unauth_homes = client.get("/api/homes")
        self.assertEqual(res_unauth_homes.status_code, 401)


if __name__ == "__main__":
    unittest.main()

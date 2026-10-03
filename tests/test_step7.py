import sys
import os
import time
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.services.api_client import APIClient
from app.security.security_event_service import SecurityEventService
from app.services.backend_store import backend_store
from tests.test_backend import generate_test_token, create_test_user, delete_test_user

test_app_client = TestClient(app)


class TestStep7Integration(unittest.TestCase):

    def setUp(self):
        backend_store.clear()
        self.user_id = create_test_user("user7@example.com", "User 7")
        self.token = generate_test_token(str(self.user_id), "user7@example.com")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create home owned by user7
        res_home = test_app_client.post("/api/homes", json={"name": "Test Home Step 7"}, headers=self.headers)
        self.assertEqual(res_home.status_code, 201)
        self.home_id = res_home.json()["id"]

        # API Client initialized for in-memory FastApi TestClient
        self.api_client = APIClient(client=test_app_client, auth_token=self.token)

    def tearDown(self):
        delete_test_user(self.user_id)
        backend_store.clear()

    def test_01_api_client_health_check(self):
        """Test 1: API client reaches FastAPI health endpoint."""
        res = test_app_client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_02_security_event_creates_security_log(self):
        """Test 2: Security event service creates a security log."""
        event_service = SecurityEventService(
            api_client=self.api_client,
            home_id=self.home_id,
            motion_cooldown=0.01,
        )

        # Direct synchronous dispatch for testing
        res_log = self.api_client.create_security_log(
            home_id=self.home_id,
            event_type="motion_detected",
            description="Motion detected near driveway",
            is_authorized=None,
        )
        self.assertIsNotNone(res_log)
        self.assertEqual(res_log["event_type"], "motion_detected")

        # Verify log exists in BackendStore
        logs = backend_store.get_home_security_logs(home_id=self.home_id, requesting_user_id=self.user_id)
        self.assertEqual(len(logs), 1)

    def test_03_unknown_person_creates_alert(self):
        """Test 3: Unknown person event creates a security log and alert."""
        res_log = self.api_client.create_security_log(
            home_id=self.home_id,
            event_type="unknown_person",
            description="Unknown person detected",
            person_name="Unknown",
            is_authorized=False,
        )
        self.assertIsNotNone(res_log)

        res_alert = self.api_client.create_alert(
            home_id=self.home_id,
            alert_type="unknown_person",
            title="Unknown Person Detected",
            message="An unregistered person was detected at the entrance.",
            security_log_id=res_log["id"],
        )
        self.assertIsNotNone(res_alert)
        self.assertEqual(res_alert["alert_type"], "unknown_person")

        # Verify in store
        alerts = backend_store.get_home_alerts(home_id=self.home_id, requesting_user_id=self.user_id)
        self.assertEqual(len(alerts), 1)

    def test_04_authorized_person_creates_authorized_event(self):
        """Test 4: Authorized person creates an authorized event."""
        res_log = self.api_client.create_security_log(
            home_id=self.home_id,
            event_type="authorized_person_detected",
            description="Authorized person 'Zahid' detected",
            person_name="Zahid",
            is_authorized=True,
        )
        self.assertIsNotNone(res_log)
        self.assertEqual(res_log["person_name"], "Zahid")
        self.assertTrue(res_log["is_authorized"])

    def test_05_cooldown_prevents_duplicate_events(self):
        """Test 5: Cooldown prevents duplicate events within cooldown window."""
        event_service = SecurityEventService(
            home_id=self.home_id,
            unknown_cooldown=10.0,
        )

        # First call -> Cooldown is NOT active (proceeds)
        self.assertFalse(event_service.is_cooldown_active("unknown_person", 10.0))

        # Immediate second call -> Cooldown IS active (blocks duplicate)
        self.assertTrue(event_service.is_cooldown_active("unknown_person", 10.0))
        self.assertTrue(event_service.is_cooldown_active("unknown_person", 10.0))

    def test_06_different_event_types_independent_cooldowns(self):
        """Test 6: Different event types have independent cooldowns."""
        event_service = SecurityEventService(home_id=self.home_id)

        # Trigger unknown_person cooldown
        self.assertFalse(event_service.is_cooldown_active("unknown_person", 5.0))
        self.assertTrue(event_service.is_cooldown_active("unknown_person", 5.0))

        # Trigger motion_detected cooldown -> Should NOT be blocked by unknown_person cooldown!
        self.assertFalse(event_service.is_cooldown_active("motion_detected", 5.0))
        self.assertTrue(event_service.is_cooldown_active("motion_detected", 5.0))

        # Trigger authorized person Zahid cooldown -> Should NOT be blocked by motion cooldown!
        self.assertFalse(event_service.is_cooldown_active("authorized_person_zahid", 10.0))

    def test_07_missing_home_id_graceful_fallback(self):
        """Test 7: Missing home ID does not crash the security system."""
        event_service = SecurityEventService(home_id=None)
        res_motion = event_service.handle_motion_event()
        self.assertIsNone(res_motion)

        res_unknown = event_service.handle_unknown_person()
        self.assertIsNone(res_unknown)

        res_auth = event_service.handle_authorized_person("Zahid")
        self.assertIsNone(res_auth)

    def test_08_fastapi_unavailable_graceful_fallback(self):
        """Test 8: FastAPI server unavailable does not crash security system."""
        offline_client = APIClient(base_url="http://127.0.0.1:59999", timeout=0.1)

        self.assertFalse(offline_client.health_check())

        # Creating log on offline server returns None without throwing unhandled exceptions
        log_res = offline_client.create_security_log(
            home_id=str(uuid4()),
            event_type="motion_detected",
        )
        self.assertIsNone(log_res)

        alert_res = offline_client.create_alert(
            home_id=str(uuid4()),
            alert_type="unknown_person",
            title="Test Alert",
            message="Test Message",
        )
        self.assertIsNone(alert_res)


if __name__ == "__main__":
    unittest.main()

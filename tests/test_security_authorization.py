import sys
import os
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.services.backend_store import backend_store
from tests.test_backend import generate_test_token

client = TestClient(app)


class TestSecurityAuthorization(unittest.TestCase):
    """Section 26 Security Test: Cross-User Resource Isolation & RLS Authorization Verification.

    Verifies User A (Home A) and User B (Home B):
    - User A can access Home A.
    - User A CANNOT access Home B (HTTP 403 Forbidden).
    - User B can access Home B.
    - User B CANNOT access Home A (HTTP 403 Forbidden).
    - Cross-user member, device, log, and alert access is strictly blocked.
    """

    def setUp(self):
        backend_store.clear()

        # User A Setup
        self.user_a_id = uuid4()
        self.token_a = generate_test_token(str(self.user_a_id), "usera@example.com")
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

        # User B Setup
        self.user_b_id = uuid4()
        self.token_b = generate_test_token(str(self.user_b_id), "userb@example.com")
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

        # 1. Create Home A owned by User A
        res_home_a = client.post("/api/homes", json={"name": "Home A", "address": "111 Alpha St"}, headers=self.headers_a)
        self.assertEqual(res_home_a.status_code, 201)
        self.home_a_id = res_home_a.json()["id"]

        # 2. Create Home B owned by User B
        res_home_b = client.post("/api/homes", json={"name": "Home B", "address": "222 Beta Rd"}, headers=self.headers_b)
        self.assertEqual(res_home_b.status_code, 201)
        self.home_b_id = res_home_b.json()["id"]

    def test_01_user_can_access_own_home(self):
        """Verify User A accesses Home A and User B accesses Home B."""
        # User A -> Home A
        res_a = client.get(f"/api/homes/{self.home_a_id}", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(res_a.json()["name"], "Home A")

        # User B -> Home B
        res_b = client.get(f"/api/homes/{self.home_b_id}", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["name"], "Home B")

    def test_02_cross_user_home_access_forbidden(self):
        """Verify User A CANNOT access Home B and User B CANNOT access Home A."""
        # User A tries to access Home B -> 403 Forbidden
        res_a_on_b = client.get(f"/api/homes/{self.home_b_id}", headers=self.headers_a)
        self.assertEqual(res_a_on_b.status_code, 403)

        # User B tries to access Home A -> 403 Forbidden
        res_b_on_a = client.get(f"/api/homes/{self.home_a_id}", headers=self.headers_b)
        self.assertEqual(res_b_on_a.status_code, 403)

    def test_03_cross_user_member_access_forbidden(self):
        """Verify User A cannot add or view members of Home B."""
        # User B adds Member to Home B
        res_m_b = client.post(
            f"/api/homes/{self.home_b_id}/members",
            json={"name": "Family Member B"},
            headers=self.headers_b,
        )
        self.assertEqual(res_m_b.status_code, 201)
        member_b_id = res_m_b.json()["id"]

        # User A tries to view members of Home B -> 403 Forbidden
        res_a_view_m = client.get(f"/api/homes/{self.home_b_id}/members", headers=self.headers_a)
        self.assertEqual(res_a_view_m.status_code, 403)

        # User A tries to add member to Home B -> 403 Forbidden
        res_a_add_m = client.post(
            f"/api/homes/{self.home_b_id}/members",
            json={"name": "Hacker Member"},
            headers=self.headers_a,
        )
        self.assertEqual(res_a_add_m.status_code, 403)

        # User A tries to update Member B -> 403 Forbidden
        res_a_update_m = client.put(
            f"/api/members/{member_b_id}",
            json={"name": "Modified Name"},
            headers=self.headers_a,
        )
        self.assertEqual(res_a_update_m.status_code, 403)

    def test_04_cross_user_device_log_alert_access_forbidden(self):
        """Verify User A cannot view devices, security logs, or alerts belonging to Home B."""
        # User B creates Device, Log, Alert in Home B
        res_dev_b = client.post(f"/api/homes/{self.home_b_id}/devices", json={"device_name": "Cam B", "device_type": "camera"}, headers=self.headers_b)
        self.assertEqual(res_dev_b.status_code, 201)

        res_log_b = client.post(f"/api/homes/{self.home_b_id}/security-logs", json={"event_type": "motion_detected"}, headers=self.headers_b)
        self.assertEqual(res_log_b.status_code, 201)

        res_alert_b = client.post(f"/api/homes/{self.home_b_id}/alerts", json={"alert_type": "unknown_person", "title": "Intruder Alert", "message": "Unknown person near Home B"}, headers=self.headers_b)
        self.assertEqual(res_alert_b.status_code, 201)
        alert_b_id = res_alert_b.json()["id"]

        # User A tries to access Home B devices, logs, alerts -> All return 403 Forbidden
        self.assertEqual(client.get(f"/api/homes/{self.home_b_id}/devices", headers=self.headers_a).status_code, 403)
        self.assertEqual(client.get(f"/api/homes/{self.home_b_id}/security-logs", headers=self.headers_a).status_code, 403)
        self.assertEqual(client.get(f"/api/homes/{self.home_b_id}/alerts", headers=self.headers_a).status_code, 403)
        self.assertEqual(client.put(f"/api/alerts/{alert_b_id}/read", json={"is_read": True}, headers=self.headers_a).status_code, 403)


if __name__ == "__main__":
    unittest.main()

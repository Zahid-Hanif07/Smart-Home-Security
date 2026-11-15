import sys
import os
import jwt
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.config.backend_settings import settings
from app.services.backend_store import backend_store
from app.repositories import home_repository, member_repository, face_repository, is_supabase_configured
from tests.test_backend import create_test_user, delete_test_user

client = TestClient(app)


def generate_signed_jwt(user_id: str, email: str = "user@example.com") -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_metadata": {"name": "Test User"},
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


class TestStep11Repositories(unittest.TestCase):

    def setUp(self):
        backend_store.clear()
        self.user1_id = create_test_user("user1@example.com", "User 1")
        self.user2_id = create_test_user("user2@example.com", "User 2")

        self.token1 = generate_signed_jwt(str(self.user1_id), "user1@example.com")
        self.token2 = generate_signed_jwt(str(self.user2_id), "user2@example.com")

        self.headers1 = {"Authorization": f"Bearer {self.token1}"}
        self.headers2 = {"Authorization": f"Bearer {self.token2}"}

    def tearDown(self):
        delete_test_user(self.user1_id)
        delete_test_user(self.user2_id)
        backend_store.clear()

    def test_01_user_can_create_and_retrieve_own_home(self):
        """Test 1 & 2: Authenticated user creates and retrieves own home."""
        res_create = client.post("/api/homes", json={"name": "Owner Home"}, headers=self.headers1)
        self.assertEqual(res_create.status_code, 201)
        home_id = res_create.json()["id"]

        res_get = client.get(f"/api/homes/{home_id}", headers=self.headers1)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["name"], "Owner Home")

    def test_02_cross_user_home_isolation(self):
        """Test 3: User cannot access another user's home (403 Forbidden)."""
        res_create = client.post("/api/homes", json={"name": "User 1 Private Villa"}, headers=self.headers1)
        home_id = res_create.json()["id"]

        # User 2 attempts to fetch User 1's home
        res_unauth = client.get(f"/api/homes/{home_id}", headers=self.headers2)
        self.assertEqual(res_unauth.status_code, 403)

    def test_03_member_lifecycle(self):
        """Tests 4, 5, 6, 7: Member creation, retrieval, update, deletion."""
        res_home = client.post("/api/homes", json={"name": "Family Haven"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        # Create member
        res_m = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Amish", "relation": "Brother"},
            headers=self.headers1,
        )
        self.assertEqual(res_m.status_code, 201)
        member_id = res_m.json()["id"]

        # Retrieve members
        res_list = client.get(f"/api/homes/{home_id}/members", headers=self.headers1)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)

        # Update member
        res_update = client.put(
            f"/api/members/{member_id}",
            json={"name": "Amish H.", "relation": "Elder Brother"},
            headers=self.headers1,
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["relation"], "Elder Brother")

        # Delete member
        res_del = client.delete(f"/api/members/{member_id}", headers=self.headers1)
        self.assertEqual(res_del.status_code, 204)

    def test_04_face_record_lifecycle(self):
        """Tests 8, 9, 10: Face record creation, retrieval, deletion."""
        res_home = client.post("/api/homes", json={"name": "AI Fortress"}, headers=self.headers1)
        home_id = res_home.json()["id"]

        res_m = client.post(
            f"/api/homes/{home_id}/members",
            json={"name": "Zahid", "relation": "Self"},
            headers=self.headers1,
        )
        member_id = res_m.json()["id"]

        # Create face record
        face_payload = {
            "image_path": "data/faces/Zahid/sample_01.jpg",
            "embedding": [0.05] * 128,
            "sample_count": 1,
        }
        res_f = client.post(f"/api/members/{member_id}/faces", json=face_payload, headers=self.headers1)
        self.assertEqual(res_f.status_code, 201)
        face_id = res_f.json()["id"]

        # Get faces
        res_flist = client.get(f"/api/members/{member_id}/faces", headers=self.headers1)
        self.assertEqual(res_flist.status_code, 200)
        self.assertEqual(len(res_flist.json()), 1)

        # Delete face record
        res_fdel = client.delete(f"/api/faces/{face_id}", headers=self.headers1)
        self.assertEqual(res_fdel.status_code, 204)

    def test_05_unauthorized_and_invalid_jwt_rejection(self):
        """Tests 11, 12, 13: Unauthorized requests & invalid/unsigned JWT rejection."""
        # 11. No token
        res_no_auth = client.get("/api/homes")
        self.assertEqual(res_no_auth.status_code, 401)

        # 12. Invalid token string
        res_bad_jwt = client.get("/api/homes", headers={"Authorization": "Bearer bad.token.here"})
        self.assertEqual(res_bad_jwt.status_code, 401)

        # 13. Unsigned JWT token (must be strictly rejected after Phase D security fix!)
        unsigned_token = jwt.encode({"sub": str(self.user1_id)}, key="", algorithm="none")
        res_unsigned = client.get("/api/homes", headers={"Authorization": f"Bearer {unsigned_token}"})
        self.assertEqual(res_unsigned.status_code, 401)

    def test_06_supabase_connection_status_report(self):
        """Test 14 & 15: Check whether real Supabase connection is available in current test environment."""
        configured = is_supabase_configured()
        if not configured:
            print("\n[INFO] Real Supabase integration tests could not be executed because no configured test Supabase project was available.")
        else:
            print("\n[INFO] Real Supabase connection configured and active.")

    def test_07_initial_home_retry_reuses_saved_home(self):
        first = client.post("/api/homes/initial", headers=self.headers1)
        second = client.post("/api/homes/initial", headers=self.headers1)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(len(client.get("/api/homes", headers=self.headers1).json()), 1)

    def test_08_existing_home_prevents_automatic_duplicate(self):
        existing = client.post("/api/homes", json={"name": "Existing"}, headers=self.headers1)
        ensured = client.post("/api/homes/initial", headers=self.headers1)
        self.assertEqual(existing.status_code, 201)
        self.assertEqual(ensured.status_code, 200)
        self.assertEqual(ensured.json()["id"], existing.json()["id"])
        self.assertEqual(len(client.get("/api/homes", headers=self.headers1).json()), 1)

    def test_09_owner_is_always_derived_from_verified_token(self):
        response = client.post(
            "/api/homes",
            json={"name": "Token-owned", "owner_id": str(self.user2_id)},
            headers=self.headers1,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["owner_id"], str(self.user1_id))

    def test_10_non_owner_cannot_edit_home(self):
        created = client.post("/api/homes", json={"name": "Owner-only"}, headers=self.headers1)
        home_id = created.json()["id"]
        denied = client.put(
            f"/api/homes/{home_id}",
            json={"name": "Changed by another user"},
            headers=self.headers2,
        )
        self.assertEqual(denied.status_code, 403)
        unchanged = client.get(f"/api/homes/{home_id}", headers=self.headers1)
        self.assertEqual(unchanged.json()["name"], "Owner-only")

    def test_11_unconfigured_database_does_not_fall_back_to_memory_in_production_mode(self):
        with patch.dict(os.environ, {"TEST_ISOLATED_MODE": "0", "USE_MOCK_DATABASE": "0"}):
            with patch.object(settings, "SUPABASE_URL", "https://demo-project.supabase.co"), patch.object(settings, "SUPABASE_ANON_KEY", "dummy_anon_key"):
                with self.assertRaises(Exception) as raised:
                    home_repository._get_client()
        self.assertEqual(getattr(raised.exception, "status_code", None), 503)

    def test_12_real_supabase_write_survives_a_fresh_list_read(self):
        if (
            os.getenv("RUN_LIVE_SUPABASE_TESTS") != "1"
            or not is_supabase_configured()
            or SupabaseClientManager.get_admin_client() is None
        ):
            self.skipTest("Requires explicitly enabled Supabase integration settings and service-role access.")
        created = client.post("/api/homes/initial", headers=self.headers1)
        self.assertEqual(created.status_code, 200, created.text)
        retried = client.post("/api/homes/initial", headers=self.headers1)
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(retried.json()["id"], created.json()["id"])
        listed = client.get("/api/homes", headers=self.headers1)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(created.json()["id"], [home["id"] for home in listed.json()])
        self.assertNotIn(UUID(created.json()["id"]), home_repository._in_memory_homes)


if __name__ == "__main__":
    unittest.main()

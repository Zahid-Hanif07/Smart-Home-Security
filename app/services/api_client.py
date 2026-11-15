import os
from typing import Optional, Dict, Any, List
import httpx
from app.config.settings import API_BASE_URL
from app.config.backend_settings import settings as backend_settings
from app.services.token_helper import get_effective_auth_token


class APIClient:
    """Reusable HTTP API Client for communicating with the FastAPI backend."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 3.0,
        client: Optional[Any] = None,
        custom_client: Optional[Any] = None,
    ):
        raw_url = base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self.base_url = raw_url.rstrip("/")
        # Only a user's scoped access token is accepted here. Never use the
        # Supabase service-role credential in this desktop-to-API client.
        self.auth_token = auth_token or os.getenv("SUPABASE_ACCESS_TOKEN") or os.getenv("AUTH_TOKEN") or backend_settings.SUPABASE_ACCESS_TOKEN
        self.timeout = timeout
        self.custom_client = custom_client or client

    def _get_headers(self, home_id: Optional[str] = None) -> Dict[str, str]:
        """Construct headers for HTTP requests."""
        headers = {"Content-Type": "application/json"}
        token = self.auth_token or get_effective_auth_token(home_id=home_id)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def health_check(self) -> bool:
        """Check FastAPI backend connectivity via GET /health.

        Returns:
            bool: True if backend is online and returns status ok.
        """
        try:
            url = f"{self.base_url}/health" if not self.custom_client else "/health"
            if self.custom_client:
                res = self.custom_client.get(url)
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.get(url)
            if res.status_code == 200:
                data = res.json()
                return data.get("status") == "ok"
            return False
        except Exception:
            return False

    def create_security_log(
        self,
        home_id: str,
        event_type: str,
        description: Optional[str] = None,
        person_name: Optional[str] = None,
        is_authorized: Optional[bool] = None,
        device_id: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Report a security log event to FastAPI endpoint POST /api/homes/{home_id}/security-logs."""
        if not home_id:
            print("Backend reporting skipped: SECURITY_HOME_ID not configured.")
            return None

        url = f"{self.base_url}/api/homes/{home_id}/security-logs" if not self.custom_client else f"/api/homes/{home_id}/security-logs"
        payload = {
            "event_type": event_type,
            "description": description,
            "person_name": person_name,
            "is_authorized": is_authorized,
            "device_id": device_id,
            "image_path": image_path,
        }

        try:
            headers = self._get_headers(home_id=home_id)
            if self.custom_client:
                res = self.custom_client.post(url, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.post(url, json=payload, headers=headers)

            if res.status_code in (200, 201):
                return res.json()
            print(f"APIClient warning: POST {url} returned status code {res.status_code}")
            return None
        except Exception:
            print("Backend unavailable: security event could not be reported.")
            return None

    def create_alert(
        self,
        home_id: str,
        alert_type: str,
        title: str,
        message: str,
        security_log_id: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Report a security alert to FastAPI endpoint POST /api/homes/{home_id}/alerts."""
        if not home_id:
            print("Backend alert skipped: SECURITY_HOME_ID not configured.")
            return None

        url = f"{self.base_url}/api/homes/{home_id}/alerts" if not self.custom_client else f"/api/homes/{home_id}/alerts"
        payload = {
            "alert_type": alert_type,
            "title": title,
            "message": message,
            "security_log_id": security_log_id,
            "image_path": image_path,
        }

        try:
            headers = self._get_headers(home_id=home_id)
            if self.custom_client:
                res = self.custom_client.post(url, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.post(url, json=payload, headers=headers)

            if res.status_code in (200, 201):
                return res.json()
            print(f"APIClient warning: POST {url} returned status code {res.status_code}")
            return None
        except Exception:
            print("Backend unavailable: alert could not be reported.")
            return None

    def get_home_face_records(self, home_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch registered face records for a home from GET /api/homes/{home_id}/face-records."""
        if not home_id:
            return None

        url = f"{self.base_url}/api/homes/{home_id}/face-records" if not self.custom_client else f"/api/homes/{home_id}/face-records"
        try:
            headers = self._get_headers(home_id=home_id)
            if self.custom_client:
                res = self.custom_client.get(url, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.get(url, headers=headers)

            if res.status_code == 200:
                return res.json()
            print(f"APIClient warning: GET {url} returned status code {res.status_code}")
            return None
        except Exception:
            print("Backend unavailable: face records could not be retrieved.")
            return None

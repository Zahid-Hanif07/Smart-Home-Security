import os
from typing import Optional, Dict, Any
import httpx
from app.config.settings import API_BASE_URL


class APIClient:
    """Reusable HTTP API Client for communicating with the FastAPI backend."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 3.0,
        client: Optional[Any] = None,
    ):
        raw_url = base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self.base_url = raw_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.custom_client = client

    def _get_headers(self) -> Dict[str, str]:
        """Construct headers for HTTP requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
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
            if self.custom_client:
                res = self.custom_client.post(url, json=payload, headers=self._get_headers())
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.post(url, json=payload, headers=self._get_headers())

            if res.status_code in (200, 201):
                return res.json()
            print(f"APIClient warning: POST {url} returned status code {res.status_code}")
            return None
        except Exception as e:
            print(f"Backend unavailable: security event could not be reported. Details: {e}")
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
            if self.custom_client:
                res = self.custom_client.post(url, json=payload, headers=self._get_headers())
            else:
                with httpx.Client(timeout=self.timeout) as c:
                    res = c.post(url, json=payload, headers=self._get_headers())

            if res.status_code in (200, 201):
                return res.json()
            print(f"APIClient warning: POST {url} returned status code {res.status_code}")
            return None
        except Exception as e:
            print(f"Backend unavailable: alert could not be reported. Details: {e}")
            return None

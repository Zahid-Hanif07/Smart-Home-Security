import os
import time
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from app.config.settings import (
    SECURITY_HOME_ID,
    UNKNOWN_PERSON_COOLDOWN,
    MOTION_COOLDOWN,
    AUTHORIZED_PERSON_COOLDOWN,
)
from app.services.api_client import APIClient


class SecurityEventService:
    """Service converting AI vision detection results into debounced backend API events and alerts.

    Features:
    - Independent monotonic event cooldowns for motion, authorized faces, and unknown faces.
    - Automatic alert creation for unknown person detections.
    - Asynchronous non-blocking HTTP dispatch using ThreadPoolExecutor.
    - Graceful fallback when home ID is missing or backend server is offline.
    """

    def __init__(
        self,
        api_client: Optional[APIClient] = None,
        home_id: Optional[str] = None,
        unknown_cooldown: float = UNKNOWN_PERSON_COOLDOWN,
        motion_cooldown: float = MOTION_COOLDOWN,
        authorized_cooldown: float = AUTHORIZED_PERSON_COOLDOWN,
    ):
        self.api_client = api_client or APIClient()
        self.home_id = home_id or os.getenv("SECURITY_HOME_ID") or SECURITY_HOME_ID
        self.unknown_cooldown = unknown_cooldown
        self.motion_cooldown = motion_cooldown
        self.authorized_cooldown = authorized_cooldown

        # Monotonic timestamp dict tracking last execution per event key
        self._last_event_times: Dict[str, float] = {}

        # Non-blocking background thread pool for HTTP requests
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="security_event_worker")

    def set_home_id(self, home_id: Optional[str]) -> None:
        """Dynamically configure target home UUID."""
        self.home_id = home_id

    def is_cooldown_active(self, event_key: str, cooldown_duration: float) -> bool:
        """Check if an event key is currently within its cooldown window.

        Args:
            event_key (str): Unique key identifier for event type/person.
            cooldown_duration (float): Minimum seconds required between reports.

        Returns:
            bool: True if cooldown is active (should skip reporting), False otherwise.
        """
        now = time.monotonic()
        last_time = self._last_event_times.get(event_key, 0.0)

        if (now - last_time) < cooldown_duration:
            return True

        self._last_event_times[event_key] = now
        return False

    def handle_motion_event(self) -> Optional[Dict[str, Any]]:
        """Report a motion_detected event if cooldown has expired."""
        if not self.home_id:
            return None

        if self.is_cooldown_active("motion_detected", self.motion_cooldown):
            return None

        def _dispatch():
            return self.api_client.create_security_log(
                home_id=self.home_id,
                event_type="motion_detected",
                description="Motion detected by camera security system.",
                person_name=None,
                is_authorized=None,
            )

        self._executor.submit(_dispatch)
        return {"status": "queued", "event_type": "motion_detected"}

    def handle_authorized_person(self, person_name: str) -> Optional[Dict[str, Any]]:
        """Report an authorized_person_detected event if cooldown has expired."""
        if not self.home_id or not person_name:
            return None

        event_key = f"authorized_person_{person_name.lower()}"
        if self.is_cooldown_active(event_key, self.authorized_cooldown):
            return None

        def _dispatch():
            return self.api_client.create_security_log(
                home_id=self.home_id,
                event_type="authorized_person_detected",
                description=f"Authorized person '{person_name}' detected.",
                person_name=person_name,
                is_authorized=True,
            )

        self._executor.submit(_dispatch)
        return {"status": "queued", "event_type": "authorized_person_detected", "person_name": person_name}

    def handle_unknown_person(self) -> Optional[Dict[str, Any]]:
        """Report an unknown_person event and trigger a security alert if cooldown has expired."""
        if not self.home_id:
            return None

        if self.is_cooldown_active("unknown_person", self.unknown_cooldown):
            return None

        def _dispatch():
            # 1. Create security log
            log_res = self.api_client.create_security_log(
                home_id=self.home_id,
                event_type="unknown_person",
                description="Unknown person detected at entrance.",
                person_name="Unknown",
                is_authorized=False,
            )

            log_id = log_res.get("id") if isinstance(log_res, dict) else None

            # 2. Create security alert
            self.api_client.create_alert(
                home_id=self.home_id,
                alert_type="unknown_person",
                title="Unknown Person Detected",
                message="An unregistered person was detected at the entrance.",
                security_log_id=log_id,
            )

        self._executor.submit(_dispatch)
        return {"status": "queued", "event_type": "unknown_person"}

    def process_recognition_results(
        self, motion_detected: bool, recognition_results: list[dict]
    ) -> None:
        """Process frame detection results and report appropriate security events."""
        if not self.home_id:
            return

        # 1. Check for face recognition results first
        if recognition_results:
            has_unknown = False
            for rec in recognition_results:
                name = rec.get("name", "Unknown")
                matched = rec.get("matched", False)

                if matched and name.upper() != "UNKNOWN":
                    self.handle_authorized_person(name)
                else:
                    has_unknown = True

            if has_unknown:
                self.handle_unknown_person()
            return

        # 2. If no faces, report motion event if motion was detected
        if motion_detected:
            self.handle_motion_event()

    def shutdown(self) -> None:
        """Cleanly terminate background thread pool."""
        self._executor.shutdown(wait=False)

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from app.config.settings import CAMERA_INDEX, FRAME_DELAY_MS
from app.security.security_service import SecurityService
from app.security.face_occlusion_runtime import FaceOcclusionRuntime
from app.streaming.frame_manager import get_frame_manager
from app.streaming.frame_publisher import FramePublisher
from app.services.face_occlusion_diagnostic_publisher import FaceOcclusionDiagnosticPublisher
from datetime import datetime, timezone


class CameraWorker(QThread):
    """Worker thread that continuously reads webcam frames, executes security processing,
    and emits Qt signals to update the dashboard UI without blocking the interface.
    """

    # Qt Signals for UI communication
    frame_processed = Signal(QImage)
    status_updated = Signal(bool, bool)  # (motion_detected, face_detected)
    identity_updated = Signal(str, str)  # (identity_name, authorization_status)
    backend_status_updated = Signal(bool)  # True if backend online, False if offline
    face_occlusion_updated = Signal(object)
    log_event = Signal(str)
    error_occurred = Signal(str)
    stream_stopped = Signal()

    def __init__(self, camera_index: int = CAMERA_INDEX, home_id: str = None, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = False
        # The configured home is not authoritative for a paired camera.
        self.home_id = None
        self.security_service = SecurityService(home_id=self.home_id)
        self.face_occlusion_runtime = FaceOcclusionRuntime()
        self._last_face_occlusion_frame = -1
        self._stale_face_occlusion_frame = None
        set_face_occlusion_runtime = getattr(
            self.security_service,
            "set_face_occlusion_runtime",
            None,
        )
        if set_face_occlusion_runtime is not None:
            set_face_occlusion_runtime(self.face_occlusion_runtime)
        self.security_service.event_service.on_delivery_status = self._on_event_delivery_status
        self.frame_manager = get_frame_manager()
        self.frame_publisher = FramePublisher()
        self.face_occlusion_publisher = FaceOcclusionDiagnosticPublisher(
            session_provider=getattr(
                self.frame_publisher,
                "get_session_snapshot",
                lambda: None,
            ),
        )
        self.frame_publisher.start()

    def _on_event_delivery_status(self, event_type: str, succeeded: bool) -> None:
        state = "delivered" if succeeded else "delivery failed"
        self.log_event.emit(f"Backend {state}: {event_type}")


    def set_home_id(self, home_id: str) -> None:
        """Update backend home ID in SecurityService."""
        self.home_id = home_id
        self.security_service.set_home_id(home_id)

    def _sync_resolved_home_id(self) -> None:
        """Apply publisher identity changes on the camera-processing thread."""
        home_id = self.frame_publisher.resolved_home_id
        if home_id is not None and home_id != self.home_id:
            self.set_home_id(home_id)

    def reload_face_database(self) -> None:
        """Reload face database embeddings in SecurityService."""
        self.security_service.reload_face_database()
        self.log_event.emit("Face database reloaded in camera worker.")

    def _emit_face_occlusion_updates(self) -> None:
        current_frame = self.security_service.frame_sequence
        for diagnostic in self.face_occlusion_runtime.drain_results():
            if diagnostic.frame_sequence >= 0 and diagnostic.frame_sequence < self._last_face_occlusion_frame:
                continue
            if diagnostic.frame_sequence >= 0 and self.face_occlusion_runtime.is_stale(
                diagnostic,
                current_frame_sequence=current_frame,
                max_age_frames=self.face_occlusion_runtime.max_result_age_frames,
                max_age_seconds=self.face_occlusion_runtime.max_result_age_seconds,
            ):
                continue
            self.face_occlusion_updated.emit(diagnostic)
            self.face_occlusion_publisher.submit(diagnostic)
            self._last_face_occlusion_frame = max(
                self._last_face_occlusion_frame,
                diagnostic.frame_sequence,
            )
            self._stale_face_occlusion_frame = None

        latest = self.face_occlusion_runtime.latest_result
        if (
            latest is not None
            and latest.frame_sequence >= 0
            and latest.frame_sequence >= self._last_face_occlusion_frame
            and self._stale_face_occlusion_frame != latest.frame_sequence
            and self.face_occlusion_runtime.is_stale(
                latest,
                current_frame_sequence=current_frame,
                max_age_frames=self.face_occlusion_runtime.max_result_age_frames,
                max_age_seconds=self.face_occlusion_runtime.max_result_age_seconds,
            )
        ):
            self.face_occlusion_updated.emit(
                self.face_occlusion_runtime.mark_stale(latest)
            )
            self._last_face_occlusion_frame = latest.frame_sequence
            self._stale_face_occlusion_frame = latest.frame_sequence

    def run(self) -> None:
        """Main camera execution loop running on separate QThread."""
        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            for item in self.security_service.integrity_service.inspect(None, read_ok=False, camera_open=False):
                self.security_service.event_service.handle_system_event(item)
            self.error_occurred.emit(
                "Unable to access camera. Please check camera permissions or whether another application is using the camera."
            )
            cap.release()
            self.running = False
            self.frame_publisher.stop()
            self.security_service.event_service.shutdown(wait=False)
            self.stream_stopped.emit()
            return

        self.running = True
        self.face_occlusion_runtime.start()
        self.face_occlusion_publisher.start()
        self.log_event.emit("Camera connected successfully.")
        self.log_event.emit("Security monitoring active.")
        if not self.home_id:
            self.log_event.emit("Remote face records and events will activate after device pairing.")
        if not self.frame_publisher.device_token:
            self.log_event.emit("REMOTE STREAM DISABLED: use Pair Camera to securely pair this desktop.")
        if self.security_service.recognition_service.database_error:
            self.log_event.emit(f"Face records unavailable: {self.security_service.recognition_service.database_error}")

        prev_motion = False
        prev_face = False
        prev_identity = ""
        prev_backend_status = None
        prev_frame_publish_error = None

        loop_counter = 0

        try:
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    for item in self.security_service.integrity_service.inspect(None, read_ok=False):
                        self.security_service.event_service.handle_system_event(item)
                    self.error_occurred.emit("Failed to grab frame from camera stream.")
                    break

                self._sync_resolved_home_id()

                # Run security processing pipeline (Motion -> Face -> Embedding & Recognition -> Backend Reporting)
                (
                    annotated_frame,
                    motion_detected,
                    face_detected,
                    face_count,
                    recognition_results,
                ) = self.security_service.process_security_frame(frame)
                self._emit_face_occlusion_updates()

                # Update shared thread-safe FrameManager with processed security overlay frame
                self.frame_manager.update_frame(annotated_frame)
                # Publish frame to local HTTP endpoint for inter-process FastAPI streaming
                self.frame_publisher.publish(self.frame_manager.get_latest_jpeg())

                # Periodic backend connectivity check (every 100 frames ~5s)

                if loop_counter % 100 == 0:
                    is_backend_online = self.security_service.event_service.api_client.health_check()
                    if is_backend_online != prev_backend_status:
                        self.backend_status_updated.emit(is_backend_online)
                        if is_backend_online:
                            self.log_event.emit("Backend status: ONLINE (http://127.0.0.1:8085)")
                        else:
                            self.log_event.emit("Backend status: OFFLINE (Security monitoring running locally)")
                        prev_backend_status = is_backend_online

                if self.frame_publisher.last_error != prev_frame_publish_error:
                    if self.frame_publisher.last_error:
                        self.log_event.emit(f"Camera stream publication: {self.frame_publisher.last_error}")
                    prev_frame_publish_error = self.frame_publisher.last_error

                loop_counter += 1

                # Determine identity and status
                current_identity = "—"
                current_status = "—"

                if face_detected and recognition_results:
                    primary_rec = recognition_results[0]
                    name = primary_rec.get("name", "Unknown")
                    matched = primary_rec.get("matched", False)

                    if matched and name != "Unknown":
                        current_identity = name
                        current_status = "IDENTITY MATCHED (LIVENESS UNVERIFIED)"
                    elif primary_rec.get("decision") == "unverified":
                        current_identity = "UNVERIFIED"
                        current_status = "UNVERIFIED"
                    else:
                        current_identity = "UNKNOWN"
                        current_status = "UNAUTHORIZED"
                elif face_detected:
                    current_identity = "UNKNOWN"
                    current_status = "UNAUTHORIZED"

                # Emit status log events on state transitions
                if motion_detected != prev_motion:
                    if motion_detected:
                        self.log_event.emit("Motion detected!")
                    else:
                        self.log_event.emit("Motion stopped.")
                    prev_motion = motion_detected

                if face_detected != prev_face:
                    if face_detected:
                        self.log_event.emit("Face detected in frame.")
                    else:
                        self.log_event.emit("Face no longer visible.")
                    prev_face = face_detected

                if current_identity != prev_identity:
                    if current_identity not in ("—", ""):
                        if current_status == "AUTHORIZED":
                            self.log_event.emit(f"IDENTITY CONFIRMED: {current_identity} (AUTHORIZED)")
                        else:
                            self.log_event.emit("ALERT: Unknown identity detected (UNAUTHORIZED)")
                    prev_identity = current_identity

                # Emit status signals for UI updates
                self.status_updated.emit(motion_detected, face_detected)
                self.identity_updated.emit(current_identity, current_status)

                # Convert OpenCV BGR frame to QImage for PySide6 display
                rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_img = QImage(
                    rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                ).copy()

                self.frame_processed.emit(q_img)

                # Small sleep/ms pause to prevent excessive CPU spinning
                self.msleep(max(1, FRAME_DELAY_MS))
        except Exception as e:
            self.error_occurred.emit(f"Unexpected camera error: {e}")
        finally:
            cap.release()
            self.face_occlusion_runtime.stop()
            self.face_occlusion_publisher.stop()
            self.frame_publisher.stop()
            self.running = False
            self.log_event.emit("Camera disconnected and resources released.")
            self.stream_stopped.emit()

    def stop(self) -> None:
        """Safely request thread termination and camera release."""
        self.running = False
        self.face_occlusion_runtime.stop()
        self.face_occlusion_publisher.stop()
        self.frame_publisher.stop()
        self.security_service.event_service.shutdown(wait=False)
        self.wait(2000)


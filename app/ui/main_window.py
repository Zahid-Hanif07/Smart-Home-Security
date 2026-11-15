import sys
from datetime import datetime
import time
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap, QIcon

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QTextEdit,
    QFrame,
    QMessageBox,
)
from app.ui.camera_worker import CameraWorker
from app.ui.styles import DARK_SECURITY_THEME
from app.security.face_database import FaceDatabase
from app.ui.pair_camera_dialog import PairCameraDialog
from app.security.face_occlusion_runtime import (
    STATUS_FAILED,
    STATUS_INVALID,
    STATUS_NO_FACE,
    STATUS_STALE,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
)
class MainWindow(QMainWindow):
    """Main Desktop Security Dashboard window built with PySide6."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Home Security Dashboard")
        self.resize(1150, 780)
        self.setMinimumSize(950, 680)

        self.camera_worker = None
        self.database = FaceDatabase()
        self._init_ui()
        self.setStyleSheet(DARK_SECURITY_THEME)
        self._log_event("Security Dashboard initialized.")
        self._check_initial_database_status()

    def _check_initial_database_status(self) -> None:
        """Remote face records load when the camera worker starts with a home context."""

    def _init_ui(self) -> None:
        """Initialize all PySide6 UI layouts and widgets."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. Header Banner
        header = self._create_header()
        main_layout.addWidget(header)

        # 2. Main Content Split (Left: Camera Stream | Right: Control & Status Sidebar)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # Left Column: Large Camera Live Stream Panel
        camera_panel = self._create_camera_panel()
        content_layout.addWidget(camera_panel, stretch=7)

        # Right Column: Status Cards, Controls & Event Log Sidebar
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)

        status_panel = self._create_status_panel()
        sidebar_layout.addWidget(status_panel)

        controls_panel = self._create_controls_panel()
        sidebar_layout.addWidget(controls_panel)

        log_panel = self._create_log_panel()
        sidebar_layout.addWidget(log_panel, stretch=1)

        content_layout.addLayout(sidebar_layout, stretch=4)
        main_layout.addLayout(content_layout)

    def _create_header(self) -> QWidget:
        """Create header bar containing title, subtitle, and system status badge."""
        header_card = QFrame()
        header_card.setObjectName("headerCard")

        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(15, 10, 15, 10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_label = QLabel("Smart Home Security")
        title_label.setObjectName("headerTitle")

        subtitle_label = QLabel("AI-Powered Home Monitoring, Identity & Backend Reporting System")
        subtitle_label.setObjectName("headerSubtitle")

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.lbl_system_status = QLabel("● SYSTEM ONLINE")
        self.lbl_system_status.setObjectName("systemStatusBadge")
        header_layout.addWidget(self.lbl_system_status)

        return header_card

    def _create_camera_panel(self) -> QWidget:
        """Create the central live webcam video display panel."""
        group = QGroupBox("LIVE SECURITY FEED")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)

        self.lbl_camera = QLabel()
        self.lbl_camera.setObjectName("cameraDisplayLabel")
        self.lbl_camera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_camera.setMinimumSize(640, 480)

        self._show_offline_placeholder()

        layout.addWidget(self.lbl_camera)
        return group

    def _create_status_panel(self) -> QWidget:
        """Create security status grid (Camera, Motion, Face, Identity, Status, Backend, Door)."""
        group = QGroupBox("SYSTEM STATUS")
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(10)

        # 1. Camera Status
        lbl_cam_title = QLabel("Camera:")
        lbl_cam_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_camera = QLabel("OFFLINE")
        self.badge_camera.setObjectName("statusBadge")
        self.badge_camera.setProperty("status", "offline")

        # 2. Motion Status
        lbl_motion_title = QLabel("Motion:")
        lbl_motion_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_motion = QLabel("NO MOTION")
        self.badge_motion.setObjectName("statusBadge")
        self.badge_motion.setProperty("status", "no_motion")

        # 3. Face Status
        lbl_face_title = QLabel("Face:")
        lbl_face_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_face = QLabel("NOT DETECTED")
        self.badge_face.setObjectName("statusBadge")
        self.badge_face.setProperty("status", "no_face")

        # 4. Identity Status
        lbl_identity_title = QLabel("Identity:")
        lbl_identity_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_identity = QLabel("—")
        self.badge_identity.setObjectName("statusBadge")
        self.badge_identity.setProperty("status", "no_face")

        # 5. Security Status
        lbl_status_title = QLabel("Status:")
        lbl_status_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_status = QLabel("—")
        self.badge_status.setObjectName("statusBadge")
        self.badge_status.setProperty("status", "no_face")

        # 6. Backend API Status
        lbl_backend_title = QLabel("Backend API:")
        lbl_backend_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_backend = QLabel("OFFLINE")
        self.badge_backend.setObjectName("statusBadge")
        self.badge_backend.setProperty("status", "backend_offline")

        # 7. Door Status
        lbl_door_title = QLabel("Door Lock:")
        lbl_door_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_door = QLabel("NOT CONNECTED")
        self.badge_door.setObjectName("statusBadge")
        self.badge_door.setProperty("status", "backend_offline")

        lbl_face_occ_title = QLabel("FaceOcc:")
        lbl_face_occ_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        self.badge_face_occ = QLabel("WAITING")
        self.badge_face_occ.setObjectName("statusBadge")
        self.badge_face_occ.setProperty("status", "identity_unknown")
        self.lbl_face_occ_detail = QLabel("Waiting for a diagnostic sample.")
        self.lbl_face_occ_detail.setWordWrap(True)
        self.lbl_face_occ_detail.setStyleSheet("color: #a6adc8;")

        layout.addWidget(lbl_cam_title, 0, 0)
        layout.addWidget(self.badge_camera, 0, 1)

        layout.addWidget(lbl_motion_title, 1, 0)
        layout.addWidget(self.badge_motion, 1, 1)

        layout.addWidget(lbl_face_title, 2, 0)
        layout.addWidget(self.badge_face, 2, 1)

        layout.addWidget(lbl_identity_title, 3, 0)
        layout.addWidget(self.badge_identity, 3, 1)

        layout.addWidget(lbl_status_title, 4, 0)
        layout.addWidget(self.badge_status, 4, 1)

        layout.addWidget(lbl_backend_title, 5, 0)
        layout.addWidget(self.badge_backend, 5, 1)

        layout.addWidget(lbl_door_title, 6, 0)
        layout.addWidget(self.badge_door, 6, 1)

        layout.addWidget(lbl_face_occ_title, 7, 0)
        layout.addWidget(self.badge_face_occ, 7, 1)
        layout.addWidget(self.lbl_face_occ_detail, 8, 0, 1, 2)

        return group

    def _create_controls_panel(self) -> QWidget:
        """Create camera monitoring action controls."""
        group = QGroupBox("CAMERA CONTROL & SECURITY MONITORING")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(10)

        cam_btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("START CAMERA")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_camera)

        self.btn_stop = QPushButton("STOP CAMERA")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_camera)

        cam_btn_layout.addWidget(self.btn_start)
        cam_btn_layout.addWidget(self.btn_stop)

        layout.addLayout(cam_btn_layout)

        self.btn_pair_camera = QPushButton("Pair Camera")
        self.btn_pair_camera.setObjectName("btnPairCamera")
        self.btn_pair_camera.clicked.connect(self.open_pair_camera_dialog)
        layout.addWidget(self.btn_pair_camera)

        return group

    def _create_log_panel(self) -> QWidget:
        """Create timestamped event log panel."""
        group = QGroupBox("SECURITY EVENT LOG")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)

        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("logTextEdit")
        self.txt_log.setReadOnly(True)

        layout.addWidget(self.txt_log)
        return group

    def _show_offline_placeholder(self) -> None:
        """Show static placeholder label when camera is stopped."""
        self.lbl_camera.setText(
            "📷  CAMERA OFFLINE\n\nClick '[ START CAMERA ]' to begin live monitoring."
        )

    # -------------------------------------------------------------------------
    # Camera Control & Worker Communication
    # -------------------------------------------------------------------------

    def start_camera(self) -> None:
        """Safely start the camera worker QThread."""
        if self.camera_worker is not None and self.camera_worker.isRunning():
            return

        self._log_event("Starting camera stream...")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._update_badge(self.badge_camera, "ONLINE", "online")
        self._reset_face_occlusion_display()

        # Create worker thread
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_processed.connect(self.on_frame_received)
        self.camera_worker.status_updated.connect(self.on_status_updated)
        self.camera_worker.identity_updated.connect(self.on_identity_updated)
        self.camera_worker.backend_status_updated.connect(self.on_backend_status_updated)
        self.camera_worker.face_occlusion_updated.connect(self.on_face_occlusion_updated)
        self.camera_worker.log_event.connect(self._log_event)
        self.camera_worker.error_occurred.connect(self.on_camera_error)
        self.camera_worker.stream_stopped.connect(self.on_stream_stopped)

        self.camera_worker.start()

    def open_pair_camera_dialog(self) -> None:
        dialog = PairCameraDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        publisher_ready = True
        if self.camera_worker is not None:
            publisher_ready = self.camera_worker.frame_publisher.reload_device_credential()
        message = "The device credential was stored securely in Windows Credential Manager."
        if not publisher_ready:
            message += " Restart the camera to reload the paired credential."
        QMessageBox.information(self, "Camera paired", message)

    def stop_camera(self) -> None:
        """Safely stop camera worker thread."""
        if self.camera_worker is not None and self.camera_worker.isRunning():
            self._log_event("Stopping camera stream...")
            self.camera_worker.stop()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    @Slot(QImage)
    def on_frame_received(self, q_img: QImage) -> None:
        """Render incoming QImage frame on label maintaining aspect ratio."""
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.lbl_camera.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_camera.setPixmap(scaled_pixmap)

    @Slot(bool, bool)
    def on_status_updated(self, motion_detected: bool, face_detected: bool) -> None:
        """Update motion and face status badges dynamically."""
        if motion_detected:
            self._update_badge(self.badge_motion, "MOTION DETECTED", "motion_detected")
        else:
            self._update_badge(self.badge_motion, "NO MOTION", "no_motion")

        if face_detected:
            self._update_badge(self.badge_face, "FACE DETECTED", "face_detected")
        else:
            self._update_badge(self.badge_face, "NOT DETECTED", "no_face")

    @Slot(str, str)
    def on_identity_updated(self, identity: str, status: str) -> None:
        """Update identity name and security status badges dynamically."""
        if identity == "—":
            self._update_badge(self.badge_identity, "—", "no_face")
            self._update_badge(self.badge_status, "—", "no_face")
        elif identity == "UNKNOWN":
            self._update_badge(self.badge_identity, "UNKNOWN", "identity_unknown")
            self._update_badge(self.badge_status, "UNAUTHORIZED", "unauthorized")
        elif identity == "UNVERIFIED":
            self._update_badge(self.badge_identity, "UNVERIFIED", "identity_unknown")
            self._update_badge(self.badge_status, "CHECK REQUIRED", "backend_offline")
        else:
            self._update_badge(self.badge_identity, identity, "identity_known")
            self._update_badge(self.badge_status, status, "authorized")

    @Slot(bool)
    def on_backend_status_updated(self, is_online: bool) -> None:
        """Update backend API connection badge."""
        if is_online:
            self._update_badge(self.badge_backend, "ONLINE", "backend_online")
        else:
            self._update_badge(self.badge_backend, "OFFLINE", "backend_offline")

    def on_face_occlusion_updated(self, diagnostic) -> None:
        """Render diagnostic-only FaceOcc results without changing security badges."""
        frame_sequence = getattr(diagnostic, "frame_sequence", -1)
        if frame_sequence >= 0 and frame_sequence < getattr(
            self,
            "_last_face_occ_display_frame",
            -1,
        ):
            return
        if frame_sequence >= 0:
            self._last_face_occ_display_frame = frame_sequence

        status = getattr(diagnostic, "status", STATUS_FAILED)
        labels = {
            STATUS_UNAVAILABLE: "UNAVAILABLE",
            STATUS_SUCCESS: "ANALYZED",
            STATUS_INVALID: "UNCERTAIN",
            STATUS_FAILED: "FAILED",
            STATUS_NO_FACE: "NO FACE",
            STATUS_STALE: "STALE",
        }
        display_status = labels.get(status, "WAITING")
        self._update_badge(self.badge_face_occ, display_status, "identity_unknown")

        result = getattr(diagnostic, "result", None)
        if status == STATUS_SUCCESS and result is not None:
            try:
                completed_at = float(diagnostic.completed_at)
                age_ms = max(0.0, (time.monotonic() - completed_at) * 1000.0)
                age_text = f"Age {age_ms:.0f} ms"
            except (TypeError, ValueError):
                age_text = "Age unavailable"
            self.lbl_face_occ_detail.setText(
                f"Face {diagnostic.face_index} | "
                f"Visible {result.visible_ratio:.3f} | "
                f"Inference {result.inference_ms:.1f} ms | "
                f"{age_text}"
            )
        else:
            reason = getattr(diagnostic, "reason", "diagnostic_pending")
            self.lbl_face_occ_detail.setText(f"Reason: {reason}")

    @Slot(str)
    def on_camera_error(self, error_message: str) -> None:
        """Handle camera failure gracefully without crashing app."""
        self._log_event(f"ERROR: {error_message}")
        self.stop_camera()
        self.lbl_camera.setText(f"⚠️ {error_message}")

    @Slot()
    def on_stream_stopped(self) -> None:
        """Handle worker stream shutdown completion."""
        self._update_badge(self.badge_camera, "OFFLINE", "offline")
        self._update_badge(self.badge_motion, "NO MOTION", "no_motion")
        self._update_badge(self.badge_face, "NOT DETECTED", "no_face")
        self._update_badge(self.badge_identity, "—", "no_face")
        self._update_badge(self.badge_status, "—", "no_face")
        self._update_badge(self.badge_backend, "OFFLINE", "backend_offline")
        self._reset_face_occlusion_display()
        self._show_offline_placeholder()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _update_badge(self, label: QLabel, text: str, status_prop: str) -> None:
        """Helper to update badge text and Qt style property dynamically."""
        label.setText(text)
        label.setProperty("status", status_prop)
        label.style().unpolish(label)
        label.style().polish(label)

    def _reset_face_occlusion_display(self) -> None:
        self._last_face_occ_display_frame = -1
        self._update_badge(self.badge_face_occ, "WAITING", "identity_unknown")
        self.lbl_face_occ_detail.setText("Waiting for a diagnostic sample.")

    def _log_event(self, message: str) -> None:
        """Append timestamped security log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}]  {message}"
        self.txt_log.append(log_line)

    def closeEvent(self, event) -> None:
        """Cleanly terminate camera thread on window close."""
        if self.camera_worker is not None and self.camera_worker.isRunning():
            self.camera_worker.stop()
        event.accept()


def launch_dashboard():
    """Launch PySide6 QApplication."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

import os
import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QFrame,
)
from app.security.face_detection_service import FaceDetectionService
from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_database import FaceDatabase


class FaceRegistrationDialog(QDialog):
    """Dialog widget for registering a person's face identity locally.

    Features:
    - Collects person name.
    - Captures 5–10 face sample embeddings dynamically using live camera feed.
    - Enforces face quality checks (warns if no face or multiple faces present).
    - Saves numerical embeddings to local JSON database and images to disk.
    - Operates without reopening or creating a second webcam instance.
    """

    person_registered = Signal(str)  # Emits name of newly registered person

    def __init__(self, parent=None, camera_worker=None):
        super().__init__(parent)
        self.setWindowTitle("Register New Face Identity")
        self.setMinimumSize(600, 520)
        self.setModal(True)

        self.camera_worker = camera_worker
        self.face_detector = FaceDetectionService()
        self.embedding_service = FaceEmbeddingService()
        self.database = FaceDatabase()

        self.target_samples = 8
        self.captured_embeddings = []
        self.captured_images = []
        self.is_capturing = False
        self.current_frame = None

        self._init_ui()

        # Connect to camera worker frame signal if worker is provided
        if self.camera_worker:
            self.camera_worker.frame_processed.connect(self.on_frame_received)

        # Sampling timer (captures 1 sample per 600ms when capturing is active)
        self.sample_timer = QTimer(self)
        self.sample_timer.setInterval(600)
        self.sample_timer.timeout.connect(self.capture_single_sample)

    def _init_ui(self) -> None:
        """Construct UI layout for face registration dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 1. Header / Instructions
        lbl_header = QLabel("FACE REGISTRATION WORKFLOW")
        lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(lbl_header)

        # 2. Name Input Row
        name_layout = QHBoxLayout()
        lbl_name = QLabel("Person Name:")
        lbl_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #cdd6f4;")
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Enter person's name (e.g., Zahid)")
        self.input_name.setStyleSheet(
            "padding: 8px; font-size: 13px; border: 1px solid #45475a; border-radius: 4px; background-color: #1e1e2e; color: #cdd6f4;"
        )

        name_layout.addWidget(lbl_name)
        name_layout.addWidget(self.input_name)
        layout.addLayout(name_layout)

        # 3. Live Video Preview Feed
        self.lbl_preview = QLabel()
        self.lbl_preview.setObjectName("registrationPreviewLabel")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setMinimumSize(480, 320)
        self.lbl_preview.setStyleSheet(
            "background-color: #11111b; border: 2px dashed #45475a; border-radius: 8px; color: #a6adc8;"
        )
        self.lbl_preview.setText("Camera Feed Preview\nClick '[ START CAPTURE ]' when ready.")
        layout.addWidget(self.lbl_preview)

        # 4. Feedback / Status Label
        self.lbl_status = QLabel("Ready to capture. Position your face in front of the camera.")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #fab387;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # 5. Capture Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.target_samples)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; height: 20px; background-color: #1e1e2e; color: #cdd6f4; }"
            "QProgressBar::chunk { background-color: #a6e3a1; border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        # 6. Action Buttons Layout
        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("START CAPTURE")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #b4befe; }"
        )
        self.btn_start.clicked.connect(self.start_capture)

        self.btn_save = QPushButton("SAVE")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 10px; border-radius: 4px; }"
            "QPushButton:disabled { background-color: #45475a; color: #7f849c; }"
        )
        self.btn_save.clicked.connect(self.save_registration)

        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.setStyleSheet(
            "QPushButton { background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 10px; border-radius: 4px; }"
        )
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    @Slot(QImage)
    def on_frame_received(self, q_img: QImage) -> None:
        """Receive QImage frame from CameraWorker for registration preview."""
        # Convert QImage back to BGR OpenCV format for face detection and embedding
        width = q_img.width()
        height = q_img.height()
        ptr = q_img.bits()
        ptr.setsize(height * width * 3)

        # RGB to BGR np array
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 3))
        self.current_frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Display preview in label
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.lbl_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_preview.setPixmap(scaled)

    def start_capture(self) -> None:
        """Validate input name and start sample collection loop."""
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Please enter a valid person name before starting registration.",
            )
            return

        if self.camera_worker is None or not self.camera_worker.isRunning():
            QMessageBox.warning(
                self,
                "Camera Offline",
                "Camera is offline. Please start the camera feed first.",
            )
            return

        self.captured_embeddings.clear()
        self.captured_images.clear()
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        self.input_name.setEnabled(False)
        self.is_capturing = True

        self.lbl_status.setText("Capturing samples... Please vary head angle slightly.")
        self.sample_timer.start()

    def capture_single_sample(self) -> None:
        """Process current frame, detect faces, validate count, and extract embedding sample."""
        if not self.is_capturing or self.current_frame is None:
            return

        frame = self.current_frame.copy()
        faces = self.face_detector.detect_faces(frame)

        # Rule 1: No face detected
        if len(faces) == 0:
            self.lbl_status.setText(
                "⚠️ No face detected. Please position your face inside the camera."
            )
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #f38ba8;")
            return

        # Rule 2: Multiple faces detected
        if len(faces) > 1:
            self.lbl_status.setText(
                "⚠️ Multiple faces detected. Only one person should be visible during registration."
            )
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #f38ba8;")
            return

        # Rule 3: Single face detected -> Extract embedding
        face_info = faces[0]
        embedding = self.embedding_service.compute_embedding(frame, face_info)

        if embedding is None:
            self.lbl_status.setText("⚠️ Failed to generate embedding for sample. Retrying...")
            return

        # Crop face sample image for dataset storage
        x, y, w, h = face_info["box"]
        fh, fw = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(fw - x, w), min(fh - y, h)
        crop = frame[y : y + h, x : x + w].copy() if (w > 10 and h > 10) else frame.copy()

        self.captured_embeddings.append(embedding)
        self.captured_images.append(crop)

        count = len(self.captured_embeddings)
        self.progress_bar.setValue(count)
        self.lbl_status.setText(
            f"✅ Captured sample {count}/{self.target_samples}. Slowly tilt face slightly."
        )
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #a6e3a1;")

        if count >= self.target_samples:
            self.sample_timer.stop()
            self.is_capturing = False
            self.btn_save.setEnabled(True)
            self.lbl_status.setText(
                f"🎉 Captured all {self.target_samples} face samples! Click '[ SAVE ]' to register."
            )

    def save_registration(self) -> None:
        """Save captured person embeddings and images to local database."""
        name = self.input_name.text().strip()
        if not name or not self.captured_embeddings:
            return

        success = self.database.save_person(
            name=name,
            embeddings=self.captured_embeddings,
            face_images=self.captured_images,
        )

        if success:
            QMessageBox.information(
                self,
                "Registration Complete",
                f"Person '{name}' successfully registered with {len(self.captured_embeddings)} face embeddings!",
            )
            self.person_registered.emit(name)
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Database Error",
                f"Failed to save registration for '{name}'. Check logs for details.",
            )

    def closeEvent(self, event) -> None:
        """Ensure timer is stopped on close."""
        self.sample_timer.stop()
        self.is_capturing = False
        event.accept()

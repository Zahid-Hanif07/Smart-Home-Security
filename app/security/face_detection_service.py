import os
import urllib.request
import cv2
import numpy as np
from app.config.settings import (
    FACE_CONFIDENCE_THRESHOLD,
    FACE_MODEL_PATH,
    FACE_MODEL_URL,
)


class FaceDetectionService:
    """Service class for detecting human faces using OpenCV's DNN YuNet Face Detector.

    Provides CPU-friendly multi-face detection with bounding boxes and confidence scores.
    """

    def __init__(
        self,
        model_path: str = FACE_MODEL_PATH,
        model_url: str = FACE_MODEL_URL,
        confidence_threshold: float = FACE_CONFIDENCE_THRESHOLD,
    ):
        self.model_path = model_path
        self.model_url = model_url
        self.confidence_threshold = confidence_threshold
        self.detector = None
        self.current_input_size = None

        self._initialize_detector()

    def _ensure_model_exists(self) -> bool:
        """Check if model ONNX file exists, or download it automatically."""
        if os.path.exists(self.model_path):
            return True

        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        print(f"Downloading YuNet Face Detection model to {self.model_path}...")
        try:
            urllib.request.urlretrieve(self.model_url, self.model_path)
            print("Face Detection model downloaded successfully.")
            return True
        except Exception as e:
            print(
                f"Error: Unable to download face detection model from {self.model_url}. "
                f"Details: {e}"
            )
            return False

    def _initialize_detector(self) -> bool:
        """Initialize the OpenCV FaceDetectorYN instance."""
        if not self._ensure_model_exists():
            print("Error: Face Detection model file missing. FaceDetectionService disabled.")
            return False

        try:
            # Default initial input size (640, 480); dynamically updated per frame
            self.detector = cv2.FaceDetectorYN.create(
                self.model_path,
                "",
                (640, 480),
                self.confidence_threshold,
                0.3,
                5000,
            )
            self.current_input_size = (640, 480)
            return True
        except Exception as e:
            print(f"Error initializing FaceDetectorYN: {e}")
            self.detector = None
            return False

    def detect_faces(self, frame: np.ndarray) -> list[dict]:
        """Detect faces in a given BGR camera frame.

        Args:
            frame (np.ndarray): Input BGR frame.

        Returns:
            list[dict]: List of detected faces with bounding box and confidence score:
                [{'box': (x, y, w, h), 'confidence': float}, ...]
        """
        if self.detector is None or frame is None:
            return []

        h, w = frame.shape[:2]

        # Update detector input size if frame dimensions changed
        if self.current_input_size != (w, h):
            self.detector.setInputSize((w, h))
            self.current_input_size = (w, h)

        try:
            _, faces = self.detector.detect(frame)
            if faces is None:
                return []

            detected_faces = []
            for face in faces:
                # YuNet output format: [x, y, w, h, x_re, y_re, ..., score]
                box_x, box_y, box_w, box_h = map(int, face[:4])
                confidence = float(face[14])

                if confidence >= self.confidence_threshold:
                    detected_faces.append(
                        {
                            "box": (box_x, box_y, box_w, box_h),
                            "confidence": confidence,
                            "raw": face,
                        }
                    )
            return detected_faces
        except Exception as e:
            print(f"Error during face detection: {e}")
            return []

    def draw_faces(self, frame: np.ndarray, detected_faces: list[dict]) -> np.ndarray:
        """Draw bounding boxes and identity/confidence labels around detected faces.

        Args:
            frame (np.ndarray): Frame to draw on.
            detected_faces (list[dict]): List of face dictionaries from detect_faces or recognition service.

        Returns:
            np.ndarray: Annotated frame.
        """
        for face_info in detected_faces:
            x, y, w, h = face_info["box"]
            confidence = face_info.get("confidence", 1.0)
            confidence_percent = int(confidence * 100)
            identity = face_info.get("identity") or face_info.get("name")

            # Ensure box stays within frame boundaries
            frame_h, frame_w = frame.shape[:2]
            x = max(0, x)
            y = max(0, y)
            w = min(frame_w - x, w)
            h = min(frame_h - y, h)

            if identity:
                if identity.upper() != "UNKNOWN" and face_info.get("matched", True):
                    box_color = (0, 255, 0)  # Bright Green for Authorized Identity
                    label = f"{identity}"
                else:
                    box_color = (0, 0, 255)  # Red for Unknown / Unauthorized Identity
                    label = "Unknown"
            else:
                box_color = (255, 255, 0)  # Cyan default face detection
                label = f"FACE DETECTED {confidence_percent}%"

            # Draw bounding rectangle for face
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)

            # Draw text background banner for readability
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            label_y = max(y - 10, label_size[1] + 10)

            cv2.rectangle(
                frame,
                (x, label_y - label_size[1] - 4),
                (x + label_size[0] + 6, label_y + 4),
                box_color,
                cv2.FILLED,
            )

            # Draw label text in contrasting color over background
            text_color = (0, 0, 0) if box_color != (0, 0, 255) else (255, 255, 255)
            cv2.putText(
                frame,
                label,
                (x + 3, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                text_color,
                2,
                cv2.LINE_AA,
            )

        return frame

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, list[dict]]:
        """Convenience method to detect faces and annotate frame in one call."""
        faces = self.detect_faces(frame)
        annotated_frame = self.draw_faces(frame, faces)
        return annotated_frame, faces

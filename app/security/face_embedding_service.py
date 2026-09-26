import os
import urllib.request
import cv2
import numpy as np
from app.config.settings import (
    FACE_RECOGNITION_MODEL_PATH,
    FACE_RECOGNITION_MODEL_URL,
)


class FaceEmbeddingService:
    """Service class responsible for generating numerical face embeddings using OpenCV SFace model.

    Features:
    - Loads OpenCV's SFace (FaceRecognizerSF) ONNX model once.
    - Accepts detected face region/landmarks from YuNet detector.
    - Generates 128-dimensional floating-point feature embedding vectors.
    - Completely local, lightweight, CPU-friendly execution with no external dependencies.
    """

    def __init__(
        self,
        model_path: str = FACE_RECOGNITION_MODEL_PATH,
        model_url: str = FACE_RECOGNITION_MODEL_URL,
    ):
        self.model_path = model_path
        self.model_url = model_url
        self.recognizer = None

        self._initialize_recognizer()

    def _ensure_model_exists(self) -> bool:
        """Check if SFace ONNX model exists, or download automatically if missing."""
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 1000000:
            return True

        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        print(f"Downloading SFace Face Recognition model to {self.model_path}...")
        try:
            urllib.request.urlretrieve(self.model_url, self.model_path)
            print("SFace Face Recognition model downloaded successfully.")
            return True
        except Exception as e:
            print(
                f"Error: Unable to download face recognition model from {self.model_url}. "
                f"Details: {e}"
            )
            return False

    def _initialize_recognizer(self) -> bool:
        """Initialize the cv2.FaceRecognizerSF instance."""
        if not self._ensure_model_exists():
            print("Error: Face Recognition model file missing. FaceEmbeddingService disabled.")
            return False

        try:
            self.recognizer = cv2.FaceRecognizerSF.create(self.model_path, "")
            print("FaceEmbeddingService (SFace) initialized successfully.")
            return True
        except Exception as e:
            print(f"Error initializing cv2.FaceRecognizerSF: {e}")
            self.recognizer = None
            return False

    def compute_embedding(self, frame: np.ndarray, face_info: dict) -> np.ndarray | None:
        """Generate a 128-dimensional embedding vector for a detected face.

        Args:
            frame (np.ndarray): Full input BGR image frame.
            face_info (dict): Face detection dictionary containing 'box', 'confidence', and optional 'raw'.

        Returns:
            np.ndarray | None: 128-element float32 embedding vector, or None if extraction fails.
        """
        if self.recognizer is None or frame is None or not face_info:
            return None

        try:
            aligned_face = None

            # 1. Preferred approach: Align crop using YuNet 14-element detection array (box + 5 landmarks)
            if "raw" in face_info and face_info["raw"] is not None:
                aligned_face = self.recognizer.alignCrop(frame, face_info["raw"])
            else:
                # 2. Fallback: Crop bounding box manually if raw landmarks unavailable
                box = face_info.get("box")
                if box:
                    x, y, w, h = box
                    fh, fw = frame.shape[:2]
                    x, y = max(0, x), max(0, y)
                    w, h = min(fw - x, w), min(fh - y, h)
                    if w > 10 and h > 10:
                        crop = frame[y : y + h, x : x + w]
                        aligned_face = cv2.resize(crop, (112, 112))

            if aligned_face is None or aligned_face.size == 0:
                return None

            # 3. Extract 128D feature embedding vector
            feature = self.recognizer.feature(aligned_face)
            if feature is None or feature.size == 0:
                return None

            # Ensure 1D numpy float32 vector
            embedding = feature.flatten().astype(np.float32)
            return embedding
        except Exception as e:
            print(f"Error computing face embedding: {e}")
            return None

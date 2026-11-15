"""Configuration settings for Smart Home Security Application."""

import os

from app.config.backend_settings import settings as backend_settings

# Webcam Index (0 is usually the built-in laptop camera)
CAMERA_INDEX = 0

# Window Title for OpenCV feed
WINDOW_NAME = "Smart Home Security - Motion & Face Detection"

# Delay in milliseconds between frame refreshes
FRAME_DELAY_MS = 1

# Motion Detection Configuration
GAUSSIAN_BLUR_KERNEL = (21, 21)
DELTA_THRESHOLD = 25
MIN_MOTION_AREA = 500  # Minimum pixel area of contour to register motion
ACCUMULATION_WEIGHT = 0.05  # Learning rate for running average background model

# Face Detection Configuration
FACE_CONFIDENCE_THRESHOLD = 0.6
FACE_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"
FACE_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

# Face Recognition Configuration (OpenCV SFace)
FACE_RECOGNITION_MODEL_PATH = "models/face_recognition_sface_2021dec.onnx"
FACE_RECOGNITION_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
# Cosine similarity threshold for SFace model:
# > 0.363 indicates the same person (OpenCV SFace benchmark standard for cosine similarity)
# L2 norm distance threshold: < 1.128 indicates the same person
FACE_RECOGNITION_THRESHOLD = 0.363
FACE_RECOGNITION_METRIC = "cosine"  # "cosine" or "l2"

# FaceOcc is diagnostic-only. The default is relative to the project working
# directory; deployments can point to a packaged model with FACEOCC_MODEL_PATH.
FACEOCC_DEFAULT_MODEL_PATH = os.path.join("models", "faceocc.onnx")
FACEOCC_MODEL_PATH = os.getenv("FACEOCC_MODEL_PATH") or FACEOCC_DEFAULT_MODEL_PATH
try:
    _faceocc_max_result_age_seconds = float(
        os.getenv("FACEOCC_MAX_RESULT_AGE_SECONDS", "2.0")
    )
except (TypeError, ValueError):
    _faceocc_max_result_age_seconds = 2.0
FACEOCC_MAX_RESULT_AGE_SECONDS = max(0.5, _faceocc_max_result_age_seconds)


def get_faceocc_model_path() -> str:
    """Resolve the FaceOcc model path without downloading or copying it."""
    return os.getenv("FACEOCC_MODEL_PATH") or FACEOCC_MODEL_PATH

# CPU-friendly sampling: motion is evaluated every frame, while the expensive
# face models run only on each Nth frame. Face detection is independent of motion.
FACE_PROCESS_EVERY_N_FRAMES = max(1, int(os.getenv("FACE_PROCESS_EVERY_N_FRAMES", "3")))
STREAM_STALE_AFTER_SECONDS = max(0.5, float(os.getenv("STREAM_STALE_AFTER_SECONDS", "3")))
STREAM_REPEATED_SEQUENCE_LENGTH = max(2, int(os.getenv("STREAM_REPEATED_SEQUENCE_LENGTH", "4")))
STREAM_REPLAY_REPEATS = max(2, int(os.getenv("STREAM_REPLAY_REPEATS", "3")))
STREAM_SCENE_CHANGE_DISTANCE = max(1, int(os.getenv("STREAM_SCENE_CHANGE_DISTANCE", "48")))
STREAM_EVENT_COOLDOWN = max(1.0, float(os.getenv("STREAM_EVENT_COOLDOWN", "10")))
STREAM_MAX_FRAME_BYTES = max(1024, int(os.getenv("STREAM_MAX_FRAME_BYTES", str(5 * 1024 * 1024))))
ALLOW_LOCAL_FACE_DATABASE = os.getenv("ALLOW_LOCAL_FACE_DATABASE", "false").strip().lower() == "true"
SECURITY_EVIDENCE_DIR = os.getenv("SECURITY_EVIDENCE_DIR", "data/security_evidence")
SECURITY_EVIDENCE_RETENTION_DAYS = max(1, int(os.getenv("SECURITY_EVIDENCE_RETENTION_DAYS", "30")))
FACE_QUALITY_MINIMUM_WIDTH = max(16, int(os.getenv("FACE_QUALITY_MINIMUM_WIDTH", "32")))
FACE_QUALITY_MINIMUM_SHARPNESS = max(0.0, float(os.getenv("FACE_QUALITY_MINIMUM_SHARPNESS", "4.0")))
CAMERA_OBSTRUCTION_DARKNESS = max(0.0, float(os.getenv("CAMERA_OBSTRUCTION_DARKNESS", "8.0")))
CAMERA_OBSTRUCTION_SHARPNESS = max(0.0, float(os.getenv("CAMERA_OBSTRUCTION_SHARPNESS", "1.0")))

# Local Face Database Storage Configuration
FACE_DATABASE_DIR = "data/face_database"
FACE_DATABASE_FILE = "data/face_database/embeddings.json"
FACES_DIR = "data/faces"

# Backend API Client Configuration
API_BASE_URL = backend_settings.API_BASE_URL
SECURITY_HOME_ID = backend_settings.SECURITY_HOME_ID

# Security Event Reporting Cooldowns (in seconds)
UNKNOWN_PERSON_COOLDOWN = 5.0
MOTION_COOLDOWN = 5.0
AUTHORIZED_PERSON_COOLDOWN = 10.0

# Video Streaming Configuration
STREAM_ENABLED = True
STREAM_JPEG_QUALITY = 80
STREAM_FPS = 15






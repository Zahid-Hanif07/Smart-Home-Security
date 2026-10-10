"""Configuration settings for Smart Home Security Application."""

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






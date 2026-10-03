import time
import threading
from typing import Optional, Dict, Any
import cv2
import numpy as np


class FrameManager:
    """Thread-safe frame manager maintaining the latest video frame and JPEG representation.

    Reused across PySide6 camera thread and FastAPI streaming routes without opening multiple
    webcam VideoCapture instances.
    """

    def __init__(self, default_jpeg_quality: int = 80):
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._last_update_time: float = 0.0
        self._frame_count: int = 0
        self._active_clients: int = 0
        self.default_jpeg_quality = default_jpeg_quality

    def update_frame(self, frame: np.ndarray, jpeg_quality: Optional[int] = None) -> bool:
        """Update the latest BGR frame and automatically encode to JPEG.

        Args:
            frame: NumPy BGR frame array.
            jpeg_quality: Optional JPEG quality (1-100). Defaults to self.default_jpeg_quality.

        Returns:
            bool: True if successfully updated and encoded, False otherwise.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return False

        quality = jpeg_quality if jpeg_quality is not None else self.default_jpeg_quality
        try:
            success, encoded_img = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            )
            if not success or encoded_img is None:
                return False

            jpeg_bytes = encoded_img.tobytes()

            with self._lock:
                self._latest_frame = frame.copy()
                self._latest_jpeg = jpeg_bytes
                self._last_update_time = time.time()
                self._frame_count += 1

            return True
        except Exception as e:
            # Prevent crashes during frame encoding
            return False

    def update_jpeg(self, jpeg_bytes: bytes) -> bool:
        """Directly update latest encoded JPEG bytes (e.g. from local IPC/HTTP publisher).

        Args:
            jpeg_bytes: Encoded JPEG image bytes.

        Returns:
            bool: True if updated successfully.
        """
        if not jpeg_bytes or not isinstance(jpeg_bytes, bytes):
            return False

        with self._lock:
            self._latest_jpeg = jpeg_bytes
            self._last_update_time = time.time()
            self._frame_count += 1

        return True

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get copy of the latest BGR NumPy frame."""
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Get latest encoded JPEG bytes."""
        with self._lock:
            return self._latest_jpeg

    def is_frame_available(self, max_age_seconds: float = 5.0) -> bool:
        """Check if a valid, recent frame is available."""
        with self._lock:
            if self._latest_jpeg is None or self._last_update_time == 0.0:
                return False
            return (time.time() - self._last_update_time) <= max_age_seconds

    def get_status(self) -> Dict[str, Any]:
        """Return frame manager health and status metrics."""
        with self._lock:
            now = time.time()
            age = (now - self._last_update_time) if self._last_update_time > 0 else -1.0
            available = self._latest_jpeg is not None and age >= 0 and age <= 5.0

            return {
                "streaming": True,
                "camera_available": available,
                "frame_available": available,
                "active_clients": self._active_clients,
                "frame_count": self._frame_count,
                "last_frame_age_seconds": round(age, 2) if age >= 0 else None,
            }

    def increment_clients(self) -> int:
        """Increment count of active streaming clients."""
        with self._lock:
            self._active_clients += 1
            return self._active_clients

    def decrement_clients(self) -> int:
        """Decrement count of active streaming clients."""
        with self._lock:
            self._active_clients = max(0, self._active_clients - 1)
            return self._active_clients


# Global thread-safe FrameManager singleton instance
_frame_manager_instance: Optional[FrameManager] = None
_instance_lock = threading.Lock()


def get_frame_manager() -> FrameManager:
    """Get or initialize the global FrameManager singleton instance."""
    global _frame_manager_instance
    if _frame_manager_instance is None:
        with _instance_lock:
            if _frame_manager_instance is None:
                _frame_manager_instance = FrameManager()
    return _frame_manager_instance

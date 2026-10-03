import time
import asyncio
import logging
from typing import AsyncGenerator, Optional
import cv2
import numpy as np

from app.streaming.frame_manager import FrameManager, get_frame_manager
from app.config.settings import STREAM_FPS, STREAM_JPEG_QUALITY

logger = logging.getLogger(__name__)


def create_placeholder_frame(
    width: int = 640,
    height: int = 480,
    message: str = "Waiting for camera stream...",
    quality: int = 80,
) -> bytes:
    """Generate a synthetic dark placeholder frame with status message.

    Args:
        width: Frame width in pixels.
        height: Frame height in pixels.
        message: Message text to display.
        quality: JPEG compression quality.

    Returns:
        bytes: Encoded JPEG bytes.
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Dark slate background (BGR)
    frame[:] = (35, 27, 24)

    # Outer border accent
    cv2.rectangle(frame, (10, 10), (width - 10, height - 10), (80, 70, 60), 2)

    # Title text
    title = "SMART HOME SECURITY"
    cv2.putText(
        frame,
        title,
        (width // 2 - 160, height // 2 - 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (180, 180, 180),
        2,
        cv2.LINE_AA,
    )

    # Status Message
    cv2.putText(
        frame,
        message,
        (width // 2 - 170, height // 2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 165, 255),
        2,
        cv2.LINE_AA,
    )

    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if success and encoded is not None:
        return encoded.tobytes()

    # Fallback to minimal valid JPEG if OpenCV encoding fails
    return b""


async def generate_mjpeg_stream(
    frame_manager: Optional[FrameManager] = None,
    fps: int = STREAM_FPS,
    jpeg_quality: int = STREAM_JPEG_QUALITY,
) -> AsyncGenerator[bytes, None]:
    """Async generator yielding continuous multipart MJPEG frame chunks for FastAPI StreamingResponse.

    Args:
        frame_manager: Shared FrameManager instance (defaults to singleton if None).
        fps: Target stream frames per second.
        jpeg_quality: JPEG compression quality.

    Yields:
        bytes: MJPEG multipart boundary chunk.
    """
    if frame_manager is None:
        frame_manager = get_frame_manager()

    frame_manager.increment_clients()
    logger.info("[STREAM] Stream client connected")

    frame_interval = 1.0 / max(1, fps)
    placeholder_jpeg = create_placeholder_frame(message="Waiting for camera stream...", quality=jpeg_quality)

    waiting_logged = False

    try:
        while True:
            start_time = time.time()

            if frame_manager.is_frame_available():
                jpeg_bytes = frame_manager.get_latest_jpeg()
                waiting_logged = False
            else:
                if not waiting_logged:
                    logger.info("[STREAM] Waiting for camera frame...")
                    waiting_logged = True
                jpeg_bytes = placeholder_jpeg

            if jpeg_bytes:
                header = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                footer = b"\r\n"
                yield header + jpeg_bytes + footer

            elapsed = time.time() - start_time
            sleep_duration = max(0.001, frame_interval - elapsed)
            await asyncio.sleep(sleep_duration)

    except (asyncio.CancelledError, GeneratorExit):
        logger.info("[STREAM] Stream client disconnected")
    except Exception as e:
        logger.error(f"[STREAM] Unexpected error during streaming: {e}")
    finally:
        frame_manager.decrement_clients()
        logger.info("[STREAM] Client disconnected and resources released")

import time
import threading
import queue
from typing import Optional
import httpx

from app.config.settings import API_BASE_URL, STREAM_FPS


class FramePublisher:
    """Background publisher thread that sends encoded JPEG frames to the FastAPI backend over local HTTP.

    Enables frame sharing when PySide6 desktop app and FastAPI run in separate OS processes.
    """

    def __init__(self, api_base_url: str = API_BASE_URL, target_fps: int = STREAM_FPS):
        self.api_url = f"{api_base_url.rstrip('/')}/video/frame"
        self.target_fps = target_fps
        self.min_interval = 1.0 / max(1, target_fps)
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start background publisher thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background publisher thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def publish(self, jpeg_bytes: Optional[bytes]) -> None:
        """Publish latest JPEG bytes to background queue (non-blocking)."""
        if not self._running or jpeg_bytes is None:
            return

        try:
            self._queue.put_nowait(jpeg_bytes)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(jpeg_bytes)
            except (queue.Empty, queue.Full):
                pass

    def _run(self) -> None:
        last_publish_time = 0.0
        with httpx.Client(timeout=0.5) as client:
            while self._running:
                try:
                    jpeg_bytes = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                now = time.time()
                elapsed = now - last_publish_time
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)

                try:
                    res = client.post(
                        self.api_url,
                        content=jpeg_bytes,
                        headers={"Content-Type": "image/jpeg"},
                    )
                    if res.status_code == 200:
                        last_publish_time = time.time()
                except Exception:
                    # Silently swallow backend unavailable errors (e.g. if FastAPI backend is offline)
                    pass

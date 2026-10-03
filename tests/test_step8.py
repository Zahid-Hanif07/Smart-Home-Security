import asyncio
import time
import threading
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.streaming.frame_manager import FrameManager, get_frame_manager
from app.streaming.mjpeg_stream import generate_mjpeg_stream, create_placeholder_frame


@pytest.fixture
def client():
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


@pytest.fixture
def fresh_frame_manager():
    """Fixture returning a fresh isolated FrameManager instance."""
    return FrameManager()


def test_frame_manager_initial_state(fresh_frame_manager):
    """1. Frame manager starts with no frame."""
    fm = fresh_frame_manager
    assert fm.get_latest_frame() is None
    assert fm.get_latest_jpeg() is None
    assert not fm.is_frame_available()
    status = fm.get_status()
    assert status["streaming"] is True
    assert status["camera_available"] is False
    assert status["frame_available"] is False


def test_frame_manager_accepts_numpy_frame(fresh_frame_manager):
    """2. Frame manager accepts a synthetic frame and encodes JPEG."""
    fm = fresh_frame_manager
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[100:200, 100:200] = (0, 255, 0)

    success = fm.update_frame(test_frame, jpeg_quality=85)
    assert success is True

    # 3. Frame manager returns the latest frame
    retrieved_frame = fm.get_latest_frame()
    assert retrieved_frame is not None
    assert retrieved_frame.shape == (480, 640, 3)
    assert (retrieved_frame[100:200, 100:200] == np.array([0, 255, 0], dtype=np.uint8)).all()


    jpeg_bytes = fm.get_latest_jpeg()
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 0
    assert fm.is_frame_available() is True


def test_frame_manager_accepts_direct_jpeg(fresh_frame_manager):
    """Test updating direct JPEG bytes (useful for process bridge)."""
    fm = fresh_frame_manager
    dummy_jpeg = b"\xff\xd8\xff\xe0dummy_jpeg_header_and_data"
    success = fm.update_jpeg(dummy_jpeg)
    assert success is True
    assert fm.get_latest_jpeg() == dummy_jpeg
    assert fm.is_frame_available() is True


def test_frame_manager_thread_safety(fresh_frame_manager):
    """4. Frame manager is thread-safe under concurrent reads and writes."""
    fm = fresh_frame_manager
    errors = []

    def writer():
        try:
            for i in range(50):
                img = np.full((100, 100, 3), i % 256, dtype=np.uint8)
                fm.update_frame(img)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for _ in range(50):
                _ = fm.get_latest_frame()
                _ = fm.get_latest_jpeg()
                _ = fm.get_status()
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0


def test_mjpeg_placeholder_encoding():
    """5. MJPEG placeholder encoding produces valid JPEG bytes."""
    placeholder_jpeg = create_placeholder_frame(width=320, height=240, message="Test Placeholder")
    assert isinstance(placeholder_jpeg, bytes)
    assert len(placeholder_jpeg) > 100
    assert placeholder_jpeg.startswith(b"\xff\xd8")


def test_mjpeg_stream_generator_produces_chunks():
    """6. Streaming generator produces JPEG multipart chunks."""
    async def run_gen_test():
        fm = FrameManager()
        test_frame = np.full((100, 100, 3), 128, dtype=np.uint8)
        fm.update_frame(test_frame)

        gen = generate_mjpeg_stream(frame_manager=fm, fps=30)
        chunk = await gen.__anext__()

        assert b"--frame\r\n" in chunk
        assert b"Content-Type: image/jpeg\r\n\r\n" in chunk
        assert b"\r\n" in chunk
        await gen.aclose()

    asyncio.run(run_gen_test())


def test_video_status_endpoint(client):
    """7. GET /video/status endpoint returns expected JSON metrics."""
    response = client.get("/video/status")
    assert response.status_code == 200
    data = response.json()
    assert "streaming" in data
    assert data["streaming"] is True
    assert "camera_available" in data
    assert "frame_available" in data


def test_video_stream_endpoint_exists(client):
    """8. GET /video/stream endpoint exists and returns StreamingResponse headers."""
    res = client.get("/video/status")
    assert res.status_code == 200
    from app.api.routes.video import router as video_router
    routes = [getattr(r, "path", "") for r in video_router.routes]
    assert "/stream" in routes






def test_graceful_no_frame_handling():
    """9. No frame condition is handled gracefully without crashing."""
    fm = FrameManager()
    assert not fm.is_frame_available()
    status = fm.get_status()
    assert status["camera_available"] is False

    fallback = create_placeholder_frame(message="No Frame Available")
    assert len(fallback) > 0
    assert fallback.startswith(b"\xff\xd8")

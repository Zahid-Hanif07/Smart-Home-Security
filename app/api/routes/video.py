from fastapi import APIRouter, Request, Response, status as http_status
from fastapi.responses import StreamingResponse, JSONResponse

from app.streaming.frame_manager import get_frame_manager
from app.streaming.mjpeg_stream import generate_mjpeg_stream
from app.config.settings import STREAM_FPS, STREAM_JPEG_QUALITY

router = APIRouter(tags=["Video Streaming"])


@router.get("/stream", response_class=StreamingResponse)
async def video_stream():
    """GET /video/stream - Live MJPEG video stream endpoint over HTTP.

    Streams continuous multipart JPEG frames from the camera frame pipeline.
    Viewable directly in standard web browsers or <img> HTML tags.
    """
    return StreamingResponse(
        generate_mjpeg_stream(fps=STREAM_FPS, jpeg_quality=STREAM_JPEG_QUALITY),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close",
        },
    )


@router.get("/status")
def video_status():
    """GET /video/status - Health and status endpoint for video streaming service."""
    status_data = get_frame_manager().get_status()
    return JSONResponse(content=status_data)


@router.post("/frame")
async def receive_frame(request: Request):
    """POST /video/frame - Internal endpoint to receive camera frame updates across processes."""
    body_bytes = await request.body()
    if not body_bytes:
        return JSONResponse(
            content={"status": "error", "detail": "Empty payload"},
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )

    success = get_frame_manager().update_jpeg(body_bytes)
    if success:
        return {"status": "ok"}
    else:
        return JSONResponse(
            content={"status": "error", "detail": "Failed to update frame"},
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

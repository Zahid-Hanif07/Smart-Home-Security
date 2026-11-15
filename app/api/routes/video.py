from uuid import UUID
from fastapi import APIRouter, Request, status as http_status, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.responses import FileResponse
from app.repositories.device_repository import device_repository

from app.streaming.frame_manager import get_frame_manager
from app.streaming.mjpeg_stream import generate_mjpeg_stream
from app.config.settings import STREAM_FPS, STREAM_JPEG_QUALITY
from app.config.settings import STREAM_MAX_FRAME_BYTES
from app.api.dependencies import get_current_user_id
from app.repositories.home_repository import home_repository
from app.repositories.security_log_repository import security_log_repository
from app.security.evidence_store import evidence_store
from app.security.device_session_token import validate_device_session_token

router = APIRouter(tags=["Video Streaming"])


@router.get("/stream", response_class=StreamingResponse)
async def video_stream(home_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    """GET /video/stream - Live MJPEG video stream endpoint over HTTP.

    Streams continuous multipart JPEG frames from the camera frame pipeline.
    Viewable directly in standard web browsers or <img> HTML tags.
    """
    home_repository.get_home_by_id(home_id, user_id)
    manager = get_frame_manager()
    manager_home_id = manager.get_home_id()
    if manager_home_id is None:
        raise HTTPException(
            status_code=503,
            detail="No publisher connected. Start the desktop camera application to begin streaming.",
        )
    if manager_home_id != str(home_id):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Publisher is streaming a different home ({manager_home_id}). "
                "Update SECURITY_HOME_ID in .env to match this home's UUID and restart the desktop app."
            ),
        )
    if not manager.is_frame_available():
        raise HTTPException(
            status_code=503,
            detail="Publisher is connected but no recent frames are available. Check the camera connection on the desktop.",
        )
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
def video_status(home_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    """GET /video/status - Health and status endpoint for video streaming service.

    Returns structured status including a ``reason`` field that distinguishes:
    - ``no_publisher_connected``: Desktop camera has not posted any frames yet.
    - ``publisher_home_id_mismatch``: Publisher is running for a different home.
      Update SECURITY_HOME_ID in .env to match the requested home UUID.
    - ``no_recent_frames``: Publisher connected but frames are stale or stopped.
    - ``streaming``: Live frames available; stream endpoint is open.
    """
    home_repository.get_home_by_id(home_id, user_id)
    manager = get_frame_manager()
    status_data = manager.get_status()
    manager_home_id = manager.get_home_id()
    home_id_match = manager_home_id == str(home_id)
    status_data["camera_available"] = status_data["camera_available"] and home_id_match
    status_data["frame_available"] = status_data["frame_available"] and home_id_match
    status_data["streaming"] = status_data["frame_available"]
    status_data["publisher_connected"] = manager_home_id is not None
    status_data["home_id_match"] = home_id_match
    if not manager_home_id:
        status_data["reason"] = "no_publisher_connected"
    elif not home_id_match:
        status_data["reason"] = "publisher_home_id_mismatch"
    elif not status_data["frame_available"]:
        status_data["reason"] = "no_recent_frames"
    else:
        status_data["reason"] = "streaming"
    return JSONResponse(content=status_data)


@router.post("/frame")
async def receive_frame(
    request: Request,
    x_home_id: UUID = Header(..., alias="X-Home-ID"),
    authorization: str | None = Header(None),
):
    """Receive a frame from a publisher authenticated by its device session."""
    parts = authorization.split(None, 1) if authorization else []
    if len(parts) != 2 or parts[0].lower() != "devicesession":
        raise HTTPException(
            status_code=401,
            detail="Device session authentication failed.",
            headers={"WWW-Authenticate": "DeviceSession"},
        )
    try:
        session_claims = validate_device_session_token(parts[1], expected_home_id=x_home_id)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Device session authentication failed.",
            headers={"WWW-Authenticate": "DeviceSession"},
        )
    try:
        device_state = device_repository.get_device_session_state(UUID(session_claims["device_id"]))
    except HTTPException as exc:
        # Fail closed when current revocation state cannot be verified.
        if exc.status_code >= 500:
            raise HTTPException(status_code=503, detail="Device session status is temporarily unavailable.") from exc
        raise
    if (
        device_state is None
        or str(device_state.get("status", "")).lower() == "revoked"
        or device_state.get("home_id") != x_home_id
    ):
        raise HTTPException(
            status_code=401,
            detail="Device session authentication failed.",
            headers={"WWW-Authenticate": "DeviceSession"},
        )
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > STREAM_MAX_FRAME_BYTES:
                raise HTTPException(status_code=413, detail="Frame payload exceeds the configured limit.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header.")
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > STREAM_MAX_FRAME_BYTES:
            raise HTTPException(status_code=413, detail="Frame payload exceeds the configured limit.")
    body_bytes = bytes(chunks)
    if not body_bytes:
        return JSONResponse(
            content={"status": "error", "detail": "Empty payload"},
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )

    # The stored home context comes from the signed claim, after matching the
    # caller's routing header against it; the header alone never grants access.
    success = get_frame_manager().update_jpeg(body_bytes, home_id=session_claims["home_id"])
    if success:
        return {"status": "ok"}
    else:
        return JSONResponse(
            content={"status": "error", "detail": "Failed to update frame"},
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/homes/{home_id}/evidence/{evidence_key}")
def get_event_evidence(home_id: UUID, evidence_key: str, user_id: UUID = Depends(get_current_user_id)):
    """Return a private local-development snapshot only if a home log references it."""
    home_repository.get_home_by_id(home_id, user_id)
    logs = security_log_repository.get_home_security_logs(home_id, user_id)
    if not any(item.get("image_path") == evidence_key for item in logs):
        raise HTTPException(status_code=404, detail="Evidence not found.")
    path = evidence_store.resolve(str(home_id), evidence_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename="security-evidence.jpg",
        headers={"Cache-Control": "private, no-store", "Pragma": "no-cache"},
    )

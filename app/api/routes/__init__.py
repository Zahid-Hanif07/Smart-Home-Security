from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.homes import router as homes_router
from app.api.routes.members import router as members_router
from app.api.routes.faces import router as faces_router
from app.api.routes.devices import router as devices_router
from app.api.routes.security_logs import router as security_logs_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.video import router as video_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Profile"])
api_router.include_router(homes_router, prefix="/homes", tags=["Homes"])
api_router.include_router(members_router, tags=["Home Members"])
api_router.include_router(faces_router, tags=["Face Records"])
api_router.include_router(devices_router, tags=["Devices"])
api_router.include_router(security_logs_router, tags=["Security Logs"])
api_router.include_router(alerts_router, tags=["Alerts"])
api_router.include_router(video_router, prefix="/video", tags=["Video Streaming"])

__all__ = ["api_router", "video_router"]


from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.homes import router as homes_router
from app.api.routes.members import router as members_router
from app.api.routes.faces import router as faces_router
from app.api.routes.devices import router as devices_router
from app.api.routes.security_logs import router as security_logs_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.video import router as video_router
from app.api.routes.pairing import homes_pairing_router, pairing_router
from app.api.routes.face_occlusion import router as face_occlusion_router
from app.api.routes.commands import router as commands_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Profile"])
api_router.include_router(homes_router, prefix="/homes", tags=["Homes"])
api_router.include_router(members_router, tags=["Home Members"])
api_router.include_router(faces_router, tags=["Face Records"])
api_router.include_router(devices_router, tags=["Devices"])
api_router.include_router(security_logs_router, tags=["Security Logs"])
api_router.include_router(alerts_router, tags=["Alerts"])
api_router.include_router(video_router, prefix="/video", tags=["Video Streaming"])
# Pairing: code generation is home-scoped (authenticated); claim is unauthenticated
api_router.include_router(homes_pairing_router, prefix="/homes/{home_id}/pairing-codes", tags=["Desktop Pairing"])
api_router.include_router(pairing_router, prefix="/pairing", tags=["Desktop Pairing"])
api_router.include_router(face_occlusion_router, prefix="/video/face-occlusion")
api_router.include_router(commands_router, tags=["Voice Commands"])

__all__ = [
    "api_router",
    "video_router",
    "homes_pairing_router",
    "pairing_router",
    "face_occlusion_router",
    "commands_router",
]


import logging
import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.backend_settings import settings
from app.api.routes import api_router, video_router, face_occlusion_router
from app.api.rate_limit import RequestRateLimitMiddleware

_log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """FastAPI lifespan: runs startup checks then yields for the app lifetime.

    Emits a loud WARNING when TEST_ISOLATED_MODE=1 is active so that any
    accidental activation is immediately visible in server logs.
    TEST_ISOLATED_MODE=1 is exclusively for isolated automated tests and must
    never be set in a production or shared environment.
    """
    if os.getenv("TEST_ISOLATED_MODE") == "1":
        _log.warning(
            "=================================================================\n"
            "WARNING: TEST_ISOLATED_MODE=1 is active.\n"
            "All database writes are stored IN MEMORY only and will be lost\n"
            "when this process exits.  This mode is ONLY for isolated tests.\n"
            "Remove TEST_ISOLATED_MODE from any persistent or shared environment.\n"
            "ENVIRONMENT=%s\n"
            "=================================================================",
            settings.ENVIRONMENT,
        )
    yield  # application runs here

app = FastAPI(
    title="Smart Home Security & Voice Assistant API",
    description="FastAPI Backend Foundation connected to Supabase PostgreSQL, Auth, Storage & Realtime",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestRateLimitMiddleware, requests_per_minute=settings.API_RATE_LIMIT_PER_MINUTE)

# Register API Router
app.include_router(api_router, prefix="/api")
# Also mount video router at root prefix /video for direct GET /video/stream URL access
app.include_router(video_router, prefix="/video")
app.include_router(face_occlusion_router, prefix="/video/face-occlusion")



@app.get("/", tags=["Health & Status"])
def root():
    """Root endpoint returning API metadata."""
    return {
        "title": "Smart Home Security & Voice Assistant API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health & Status"])
def health_check():
    """Health check endpoint for backend monitoring."""
    return {"status": "ok"}


def start_server():
    """Launch Uvicorn FastAPI server programmatically."""
    uvicorn.run(
        "app.api.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=True,
    )


if __name__ == "__main__":
    start_server()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.backend_settings import settings
from app.api.routes import api_router, video_router

app = FastAPI(
    title="Smart Home Security & Voice Assistant API",
    description="FastAPI Backend Foundation connected to Supabase PostgreSQL, Auth, Storage & Realtime",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix="/api")
# Also mount video router at root prefix /video for direct GET /video/stream URL access
app.include_router(video_router, prefix="/video")



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

"""
Bizpanion Backend — Main FastAPI Application
Autonomous Business Cockpit for Rural & Semi-Urban Micro-Entrepreneurs
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import upload, agents, alerts, voice, tally, market, auth, decisions
from services.supabase_client import init_supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Create audio cache directory
    os.makedirs(settings.AUDIO_CACHE_DIR, exist_ok=True)
    os.makedirs("models", exist_ok=True)
    print("✅ Bizpanion backend starting up...")
    yield
    print("🛑 Bizpanion backend shutting down...")


app = FastAPI(
    title="Bizpanion API",
    description="Autonomous Business Cockpit for Rural Entrepreneurs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure audio cache directory exists before mounting
os.makedirs(settings.AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs("models", exist_ok=True)

# Serve cached audio files
app.mount("/audio", StaticFiles(directory=settings.AUDIO_CACHE_DIR), name="audio")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(tally.router, prefix="/api/tally", tags=["tally"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])


@app.get("/")
async def root():
    return {"status": "ok", "service": "Bizpanion API v1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

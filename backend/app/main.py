from contextlib import asynccontextmanager
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings, validate_voices, get_voice_statuses, log_voice_config_startup, TTS_MODEL
from backend.app.db import init_db
from backend.app.routers.queue_router import router as queue_router
from backend.app.routers.turn_router import router as turn_router
from backend.app.routers.voice_test_router import router as voice_test_router
from backend.app.schemas import HealthResponse
from backend.app.services.audio import clear_debug_audio_dir, scan_and_clean_audio_cache
from backend.app.services.connection_manager import manager
from backend.app.services.credit_protection import count_real_calls_today
from backend.app.services.gnani import close_http_client
from backend.app.services.monitoring import (
    StructuredLoggingMiddleware,
    get_error_counts,
    get_uptime_seconds,
    get_uptime_str,
)
from backend.app.services.telugu_review import get_review_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    if settings.DEBUG_SAVE_AUDIO:
        clear_debug_audio_dir()
    # Scan audio cache and remove corrupted / invalid / < 0.3s audio
    scan_and_clean_audio_cache()
    log_voice_config_startup()
    voices_valid, bad_voice = validate_voices()
    if not voices_valid:
        print(f"[Warning] Voice {bad_voice} is not supported by timbre-v2.5. Fix backend/.env")
    if settings.DEMO_AUTOSEED:
        try:
            from backend.app.db import SessionLocal
            from backend.app.services.queue_service import auto_seed_if_empty
            with SessionLocal() as db:
                auto_seed_if_empty(db, count=4)
        except Exception as seed_err:
            print(f"[Warning] Failed to autoseed demo tokens: {seed_err}")
    yield
    # Cleanup persistent HTTP sessions
    close_http_client()


app = FastAPI(
    title="VoiceQueue API",
    description="Voice-first clinic token app for Demo Clinic",
    version="0.4.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured JSON logging middleware (P3-3)
app.add_middleware(StructuredLoggingMiddleware)

# Include Routers
app.include_router(queue_router)
app.include_router(turn_router)
app.include_router(voice_test_router)


@app.websocket("/ws/queue")
async def websocket_queue_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time live queue notifications."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive and receive any client ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


_ffmpeg_cached: bool | None = None


def _check_ffmpeg_version() -> bool:
    global _ffmpeg_cached
    if _ffmpeg_cached is not None:
        return _ffmpeg_cached
    try:
        res = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _ffmpeg_cached = (res.returncode == 0)
    except Exception:
        _ffmpeg_cached = False
    return _ffmpeg_cached


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health():
    """Health check endpoint indicating service status and configuration."""
    gnani_configured = bool(settings.GNANI_API_KEY and settings.GNANI_API_KEY.strip())
    groq_configured = bool(
        settings.GROQ_API_KEY
        and settings.GROQ_API_KEY.strip()
        and not settings.GROQ_API_KEY.startswith("your_")
    )
    ffmpeg_found = _check_ffmpeg_version()
    voices_valid, bad_voice = validate_voices()
    status_te, status_en = get_voice_statuses()
    voices_configured = bool(status_te != "empty" and status_en != "empty")

    from backend.app.services.gnani import get_last_voice_error_reason
    last_live_reason = get_last_voice_error_reason()
    if status_te != "ok":
        error_reason = status_te
    elif status_en != "ok":
        error_reason = status_en
    else:
        error_reason = last_live_reason

    rev_status = get_review_status()
    telugu_reviewed = bool(rev_status.get("reviewed_by_native_speaker", False))

    calls_used = count_real_calls_today()
    daily_cap = settings.GNANI_DAILY_CAP
    uptime_sec = get_uptime_seconds()
    uptime_str = get_uptime_str()

    return HealthResponse(
        status="ok",
        gnani_configured=gnani_configured,
        groq_configured=groq_configured,
        ffmpeg_found=ffmpeg_found,
        voices_configured=voices_configured,
        voices_valid=voices_valid,
        voice_te_status=status_te,
        voice_en_status=status_en,
        tts_model=TTS_MODEL,
        voice_te_lang="te-IN",
        voice_en_lang="en-IN",
        voice_te_voice=settings.VOICE_TE,
        voice_en_voice=settings.VOICE_EN,
        voice_error_reason=error_reason,
        invalid_voice=bad_voice,
        bad_voice=bad_voice,
        clinic_name=settings.CLINIC_NAME,
        debug_save_audio=bool(settings.DEBUG_SAVE_AUDIO),
        telugu_reviewed=telugu_reviewed,
        daily_calls_used=calls_used,
        daily_cap=daily_cap,
        cap=daily_cap,
        uptime_seconds=uptime_sec,
        uptime=uptime_str,
    )


@app.get("/dev/error-counts", tags=["Monitoring"])
def get_dev_error_counts():
    """Returns real-time counter of errors grouped by error_code (P3-3)."""
    counts = get_error_counts()
    return {
        "error_counts": counts,
        "total_errors": sum(counts.values()),
    }


@app.get("/telugu-review-status", tags=["Telugu Review"])
def telugu_review_status_endpoint():
    """Returns the review and approval status for all canonical Telugu strings."""
    return get_review_status()

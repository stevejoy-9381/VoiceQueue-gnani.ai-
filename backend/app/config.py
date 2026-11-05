import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env files from project root and backend/.env
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "backend" / ".env")


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "t")


def _get_float_optional(key: str) -> Optional[float]:
    val = os.getenv(key)
    if not val:
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


VALID_TIMBRE_VOICES: list[str] = [
    "Lavanya",
    "Lehara",
    "Suhana",
    "Varuni",
    "Yukti",
    "Saanvi",
    "Kaveri",
    "Trupti",
    "Devika",
    "Pranav",
    "Vedika",
    "Brinda",
]


class Settings:
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_MAX_CALLS: int = int(os.getenv("GNANI_MAX_CALLS", "300"))
    GNANI_DAILY_CAP: int = int(os.getenv("GNANI_DAILY_CAP", os.getenv("GNANI_MAX_CALLS", "150")))
    GNANI_RESERVE: int = int(os.getenv("GNANI_RESERVE", "40"))
    RATE_LIMIT_VOICE_10MIN: int = int(os.getenv("RATE_LIMIT_VOICE_10MIN", "6"))
    RATE_LIMIT_VOICE_DAILY: int = int(os.getenv("RATE_LIMIT_VOICE_DAILY", "30"))
    SESSION_VOICE_CAP: int = int(os.getenv("SESSION_VOICE_CAP", "10"))
    OWNER_KEY: str = os.getenv("OWNER_KEY", "").strip()
    DEMO_VIDEO_URL: str = os.getenv("DEMO_VIDEO_URL", "").strip()
    GNANI_CREDITS_PER_CALL: Optional[float] = _get_float_optional("GNANI_CREDITS_PER_CALL")
    VOICE_TE: str = os.getenv("VOICE_TE", "")
    VOICE_EN: str = os.getenv("VOICE_EN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./voicequeue.db")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]
    CLINIC_NAME: str = os.getenv("CLINIC_NAME", "Demo Clinic")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    AUDIO_CLEAN: bool = _get_bool("AUDIO_CLEAN", True)
    DEBUG_SAVE_AUDIO: bool = _get_bool("DEBUG_SAVE_AUDIO", False)


settings = Settings()


def validate_voices() -> tuple[bool, Optional[str]]:
    """Checks configured VOICE_TE and VOICE_EN against VALID_TIMBRE_VOICES."""
    if not settings.VOICE_TE or settings.VOICE_TE not in VALID_TIMBRE_VOICES:
        return False, settings.VOICE_TE or "missing"
    if not settings.VOICE_EN or settings.VOICE_EN not in VALID_TIMBRE_VOICES:
        return False, settings.VOICE_EN or "missing"
    return True, None

"""Credit protection and rate limiting service.

Guards Gnani API credits from abuse on public URLs:
- Per-IP rate limits: default 6 voice turns per 10 minutes and 30 per day.
- Per-session voice cap: default 10 voice turns.
- Global daily cap: GNANI_DAILY_CAP (default 150 real calls).
- Gnani reserve: GNANI_RESERVE (default 40 real calls), reserved exclusively for the owner.
- Owner bypass via X-Owner-Key header matching OWNER_KEY env.
- Friendly bilingual demo limit message with optional DEMO_VIDEO_URL.
"""

from collections import defaultdict
from datetime import datetime, timezone
import threading
import time
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db import SessionLocal, init_db
from backend.app.models import GnaniUsage

# Thread lock for in-memory limit tracking
_limiter_lock = threading.Lock()

# Per-IP timestamps of voice turns: ip -> list of unix timestamps
_ip_voice_timestamps: dict[str, list[float]] = defaultdict(list)

# Per-session voice turn counts: session_id -> count
_session_voice_counts: dict[str, int] = defaultdict(int)


def reset_limits():
    """Resets all in-memory rate limiting counters (primarily for unit tests)."""
    with _limiter_lock:
        _ip_voice_timestamps.clear()
        _session_voice_counts.clear()


def get_client_ip(request: Optional[Request]) -> str:
    """Extracts client IP address from request headers or connection info."""
    if not request:
        return "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def is_owner(owner_key_header: Optional[str]) -> bool:
    """Validates if the provided header matches the configured OWNER_KEY."""
    configured_key = (getattr(settings, "OWNER_KEY", "") or "").strip()
    if not configured_key:
        return False
    if not owner_key_header or not owner_key_header.strip():
        return False
    return owner_key_header.strip() == configured_key


def get_demo_limit_message() -> str:
    """Generates the friendly bilingual limit reached message with optional demo video link."""
    en_msg = "Voice demo limit reached for now. Please watch the demo video or try typing."
    te_msg = "ప్రస్తుతానికి వాయిస్ డెమో పరిమితి పూర్తయింది. దయచేసి డెమో వీడియో చూడండి లేదా టైప్ చేసి ప్రయత్నించండి."
    base_msg = f"{en_msg} / {te_msg}"
    video_url = (getattr(settings, "DEMO_VIDEO_URL", "") or "").strip()
    if video_url:
        return f"{base_msg}\n{video_url}"
    return base_msg


def count_real_calls_today(db: Optional[Session] = None) -> int:
    """Counts non-cached real calls made to Gnani today (UTC)."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    def _query(session):
        return (
            session.query(GnaniUsage)
            .filter(
                GnaniUsage.created_at >= today_start,
                GnaniUsage.cached.is_(False),
            )
            .count()
        )

    if db is not None:
        return _query(db)
    init_db()
    with SessionLocal() as session:
        return _query(session)


def check_voice_turn_limit(
    ip: str,
    session_id: str,
    is_owner_req: bool,
    db: Optional[Session] = None,
) -> Optional[str]:
    """
    Checks if a voice turn should be blocked.
    Returns:
      None if allowed.
      'demo_limit' if blocked by rate limit, session cap, reserve, or daily cap.
    """
    real_calls_today = count_real_calls_today(db)
    daily_cap = getattr(settings, "GNANI_DAILY_CAP", settings.GNANI_MAX_CALLS)
    reserve = getattr(settings, "GNANI_RESERVE", 40)

    # 1. Check absolute global daily cap
    if real_calls_today >= daily_cap:
        return "demo_limit"

    # 2. Owner bypasses reserve, session caps, and IP limits
    if is_owner_req:
        return None

    # 3. Check reserve for non-owners: block when fewer than GNANI_RESERVE remain
    if real_calls_today >= (daily_cap - reserve):
        return "demo_limit"

    with _limiter_lock:
        now = time.time()

        # 4. Check per-session voice cap
        session_cap = getattr(settings, "SESSION_VOICE_CAP", 10)
        if _session_voice_counts.get(session_id, 0) >= session_cap:
            return "demo_limit"

        # 5. Check per-IP 10-minute rate limit
        ten_min_limit = getattr(settings, "RATE_LIMIT_VOICE_10MIN", 6)
        timestamps = _ip_voice_timestamps.get(ip, [])
        ten_min_count = sum(1 for t in timestamps if t >= now - 600)
        if ten_min_count >= ten_min_limit:
            return "demo_limit"

        # 6. Check per-IP daily rate limit
        daily_limit = getattr(settings, "RATE_LIMIT_VOICE_DAILY", 30)
        daily_count = sum(1 for t in timestamps if t >= now - 86400)
        if daily_count >= daily_limit:
            return "demo_limit"

    return None


def record_voice_turn(ip: str, session_id: str):
    """Records a completed voice turn against IP and session counters."""
    with _limiter_lock:
        now = time.time()
        _ip_voice_timestamps[ip].append(now)
        # Prune timestamps older than 24h
        _ip_voice_timestamps[ip] = [t for t in _ip_voice_timestamps[ip] if t >= now - 86400]
        _session_voice_counts[session_id] = _session_voice_counts.get(session_id, 0) + 1


def can_make_tts_call(
    ip: str,
    session_id: str,
    is_owner_req: bool,
    db: Optional[Session] = None,
) -> bool:
    """
    Checks if a new live Timbre TTS call can be made (for typed turns or retries).
    If False, the spoken reply must only come from the cache (no new Timbre call).
    """
    real_calls_today = count_real_calls_today(db)
    daily_cap = getattr(settings, "GNANI_DAILY_CAP", settings.GNANI_MAX_CALLS)
    reserve = getattr(settings, "GNANI_RESERVE", 40)

    if real_calls_today >= daily_cap:
        return False

    if is_owner_req:
        return True

    # Check reserve
    if real_calls_today >= (daily_cap - reserve):
        return False

    # Check IP and session limits
    with _limiter_lock:
        now = time.time()
        session_cap = getattr(settings, "SESSION_VOICE_CAP", 10)
        if _session_voice_counts.get(session_id, 0) >= session_cap:
            return False

        ten_min_limit = getattr(settings, "RATE_LIMIT_VOICE_10MIN", 6)
        timestamps = _ip_voice_timestamps.get(ip, [])
        ten_min_count = sum(1 for t in timestamps if t >= now - 600)
        if ten_min_count >= ten_min_limit:
            return False

        daily_limit = getattr(settings, "RATE_LIMIT_VOICE_DAILY", 30)
        daily_count = sum(1 for t in timestamps if t >= now - 86400)
        if daily_count >= daily_limit:
            return False

    return True


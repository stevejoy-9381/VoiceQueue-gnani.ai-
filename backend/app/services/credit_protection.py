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
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db import SessionLocal, init_db
from backend.app.models import GnaniUsage, VoiceLog

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


def get_demo_limit_message(lang: str = "te") -> str:
    """
    Generates the friendly limit reached message in the single requested language.
    Never mixes Telugu and English together with slashes.
    """
    is_te = (lang or "").startswith("te")
    if is_te:
        base_msg = "ప్రస్తుతానికి వాయిస్ డెమో పరిమితి పూర్తయింది. దయచేసి డెమో వీడియో చూడండి లేదా టైప్ చేసి ప్రయత్నించండి."
    else:
        base_msg = "Voice demo limit reached for now. Please watch the demo video or try typing."

    video_url = (getattr(settings, "DEMO_VIDEO_URL", "") or "").strip()
    if video_url:
        return f"{base_msg}\n{video_url}"
    return base_msg


def is_demo_limits_active(client_ip: str = "127.0.0.1", request: Optional[Request] = None) -> bool:
    """
    Determines whether demo rate limits and reserve checks should be enforced.
    - DEMO_LIMITS=off (or false/0/no) -> False
    - DEMO_LIMITS=on (or true/1/yes) -> True
    - Default False when ENV=development/test or when client_ip is localhost (127.0.0.1, ::1, localhost, testclient)
    - Default True in production for remote IPs.
    """
    dl = (getattr(settings, "DEMO_LIMITS", None) or "").strip().lower()
    if dl in ("off", "false", "0", "no"):
        return False
    if dl in ("on", "true", "1", "yes"):
        return True

    env_name = getattr(settings, "ENV", "production").lower()
    if env_name in ("development", "dev", "test"):
        return False

    if client_ip in ("127.0.0.1", "localhost", "::1", "testclient"):
        return False

    return True


def _log_limit_line(
    reason: Optional[str],
    ip: str,
    session_id: str,
    counts: dict,
    blocked: bool,
    note: str = "",
) -> None:
    """Logs the rate limit evaluation in one single clean line."""
    note_str = f" ({note})" if note else ""
    print(
        f"[Limit Check] blocked={blocked}{note_str} reason={reason or 'none'} | "
        f"ip={ip} (10m={counts['ip_10m']}/{counts['ip_10m_limit']}, daily={counts['ip_daily']}/{counts['ip_daily_limit']}) | "
        f"session={session_id} ({counts['session']}/{counts['session_limit']}) | "
        f"daily={counts['daily']}/{counts['daily_cap']} (reserve={counts['reserve']}, hard_cap={counts['hard_cap']})"
    )


def get_limits_status(db: Optional[Session] = None, client_ip: str = "127.0.0.1", ip: Optional[str] = None) -> dict:
    """Returns current rate limit counters and thresholds for GET /dev/limits."""
    target_ip = ip or client_ip
    real_calls_today = count_real_calls_today(db)
    daily_cap = getattr(settings, "GNANI_DAILY_CAP", settings.GNANI_MAX_CALLS)
    hard_cap = getattr(settings, "GNANI_MAX_CALLS", 300)
    reserve = getattr(settings, "GNANI_RESERVE", 40)
    session_cap = getattr(settings, "SESSION_VOICE_CAP", 10)
    ten_min_limit = getattr(settings, "RATE_LIMIT_VOICE_10MIN", 6)
    daily_limit = getattr(settings, "RATE_LIMIT_VOICE_DAILY", 30)

    with _limiter_lock:
        now = time.time()
        ip_counts_10m = {
            ip: sum(1 for t in ts if t >= now - 600)
            for ip, ts in _ip_voice_timestamps.items()
        }
        ip_counts_daily = {
            ip: len(ts)
            for ip, ts in _ip_voice_timestamps.items()
        }
        session_counts = dict(_session_voice_counts)

    return {
        "demo_limits_active": is_demo_limits_active(client_ip),
        "real_calls_today": real_calls_today,
        "daily_cap": daily_cap,
        "hard_cap": hard_cap,
        "reserve": reserve,
        "session_voice_cap": session_cap,
        "rate_limit_voice_10min": ten_min_limit,
        "rate_limit_voice_daily": daily_limit,
        "ip_counts_10m": ip_counts_10m,
        "ip_counts_daily": ip_counts_daily,
        "session_counts": session_counts,
    }



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


def count_compare_calls(db: Optional[Session] = None) -> int:
    """Counts real STT calls made in compare / raw audio mode."""
    def _query(session):
        return (
            session.query(VoiceLog)
            .filter(
                or_(
                    VoiceLog.cleaned.is_(False),
                    VoiceLog.is_compare.is_(True),
                ),
                (VoiceLog.error.is_(None)) | (VoiceLog.error != "compare_limit"),
            )
            .count()
        )

    if db is not None:
        try:
            return _query(db)
        except Exception:
            return 0
    try:
        init_db()
        with SessionLocal() as session:
            return _query(session)
    except Exception:
        return 0


def check_compare_mode_limit(db: Optional[Session] = None) -> Optional[str]:
    """
    Checks if compare mode has reached COMPARE_MAX_CALLS (default 20).
    Returns 'compare_limit' if limit reached, None otherwise.
    """
    max_compare = getattr(settings, "COMPARE_MAX_CALLS", 20)
    used = count_compare_calls(db)
    if used >= max_compare:
        return "compare_limit"
    return None


def check_voice_turn_limit(
    ip: str,
    session_id: str,
    is_owner_req: bool,
    db: Optional[Session] = None,
    request: Optional[Request] = None,
) -> tuple[Optional[str], Optional[str], dict]:
    """
    Checks if a voice turn should be blocked.
    Returns: (error_code, limit_reason, counts_dict)
      error_code: 'demo_limit' if blocked, None if allowed.
      limit_reason: 'ip_window', 'session_cap', 'daily_cap', 'reserve', or None.
      counts_dict: current counts and limits.
    """
    real_calls_today = count_real_calls_today(db)
    daily_cap = getattr(settings, "GNANI_DAILY_CAP", settings.GNANI_MAX_CALLS)
    hard_cap = getattr(settings, "GNANI_MAX_CALLS", 300)
    reserve = getattr(settings, "GNANI_RESERVE", 40)
    session_cap = getattr(settings, "SESSION_VOICE_CAP", 10)
    ten_min_limit = getattr(settings, "RATE_LIMIT_VOICE_10MIN", 6)
    daily_limit = getattr(settings, "RATE_LIMIT_VOICE_DAILY", 30)

    with _limiter_lock:
        now = time.time()
        timestamps = _ip_voice_timestamps.get(ip, [])
        # Prune entries older than 24h
        _ip_voice_timestamps[ip] = [t for t in timestamps if t >= now - 86400]
        ten_min_count = sum(1 for t in _ip_voice_timestamps[ip] if t >= now - 600)
        daily_count = len(_ip_voice_timestamps[ip])
        session_count = _session_voice_counts.get(session_id, 0)

    counts = {
        "ip_10m": ten_min_count,
        "ip_10m_limit": ten_min_limit,
        "ip_daily": daily_count,
        "ip_daily_limit": daily_limit,
        "session": session_count,
        "session_limit": session_cap,
        "daily": real_calls_today,
        "daily_cap": daily_cap,
        "reserve": reserve,
        "hard_cap": hard_cap,
    }

    # Diagnose which limit WOULD trigger
    potential_reason = None
    if real_calls_today >= daily_cap or real_calls_today >= hard_cap:
        potential_reason = "daily_cap"
    elif real_calls_today >= (daily_cap - reserve):
        potential_reason = "reserve"
    elif session_count >= session_cap:
        potential_reason = "session_cap"
    elif ten_min_count >= ten_min_limit or daily_count >= daily_limit:
        potential_reason = "ip_window"

    # 1. Hard cap GNANI_MAX_CALLS: ALWAYS blocks, even owner
    if real_calls_today >= hard_cap:
        _log_limit_line("daily_cap", ip, session_id, counts, blocked=True, note="hard_cap")
        return "demo_limit", "daily_cap", counts

    # 2. Owner bypasses reserve, session caps, and IP limits
    if is_owner_req:
        _log_limit_line(potential_reason, ip, session_id, counts, blocked=False, note="owner_bypass")
        return None, potential_reason, counts

    # 3. Check if demo limits are active (DEMO_LIMITS env or localhost)
    if not is_demo_limits_active(ip, request):
        _log_limit_line(potential_reason, ip, session_id, counts, blocked=False, note="demo_limits_off")
        return None, potential_reason, counts

    # 4. Check global daily cap
    if real_calls_today >= daily_cap:
        _log_limit_line("daily_cap", ip, session_id, counts, blocked=True)
        return "demo_limit", "daily_cap", counts

    # 5. Check reserve for non-owners
    if real_calls_today >= (daily_cap - reserve):
        _log_limit_line("reserve", ip, session_id, counts, blocked=True)
        return "demo_limit", "reserve", counts

    # 6. Check per-session voice cap
    if session_count >= session_cap:
        _log_limit_line("session_cap", ip, session_id, counts, blocked=True)
        return "demo_limit", "session_cap", counts

    # 7. Check per-IP 10-minute rate limit and daily limit
    if ten_min_count >= ten_min_limit or daily_count >= daily_limit:
        _log_limit_line("ip_window", ip, session_id, counts, blocked=True)
        return "demo_limit", "ip_window", counts

    _log_limit_line(None, ip, session_id, counts, blocked=False)
    return None, None, counts


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


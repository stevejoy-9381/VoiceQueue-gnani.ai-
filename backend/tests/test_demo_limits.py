"""Tests for Demo Limits, Diagnosis, Owner Bypass, and Zero-Gnani Calling Guard.

Verifies:
1. Diagnose: each limit trigger provides limit_reason ('ip_window', 'session_cap', 'daily_cap', 'reserve').
2. Counts: only real Gnani calls count; blocked requests, gate failures, and typed turns do not increment.
3. DEMO_LIMITS toggle: 'off' allows local dev requests, 'on' enforces them.
4. Owner bypass: X-Owner-Key bypasses per-IP, per-session, and reserve limits, but GNANI_MAX_CALLS hard cap blocks.
5. Dev endpoints: GET /dev/limits and POST /dev/reset-limits.
6. Single language message: Telugu or English without slash-combining.
7. Zero real Gnani calls made during testing.
"""

import io
import math
import struct
import time
import wave
import pytest
from fastapi import UploadFile
from starlette.requests import Request
from starlette.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.models import GnaniUsage
from backend.app.routers.turn_router import voice_turn
from backend.app.services import credit_protection, gnani


def _make_test_wav(duration_sec: float = 1.0, amplitude: float = 0.3, freq: float = 440.0, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_frames = int(sample_rate * duration_sec)
        data = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * amplitude * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return buf.getvalue()


def _create_dummy_upload(wav_bytes: bytes, filename: str = "test.wav") -> UploadFile:
    file_obj = io.BytesIO(wav_bytes)
    return UploadFile(filename=filename, file=file_obj)


def _make_mock_request(client_ip: str = "127.0.0.1", owner_key: str | None = None) -> Request:
    headers = []
    if owner_key is not None:
        headers.append((b"x-owner-key", owner_key.encode("latin-1")))

    scope = {
        "type": "http",
        "client": (client_ip, 12345),
        "headers": headers,
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def clean_limits_state():
    credit_protection.reset_limits()
    yield
    credit_protection.reset_limits()


def test_ip_window_limit_reason(db_session, monkeypatch):
    """When per-IP 10-minute rate limit triggers, limit_reason is 'ip_window'."""
    monkeypatch.setattr(settings, "DEMO_LIMITS", "on")
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_DAILY", 50)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 50)

    stt_calls = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal stt_calls
        stt_calls += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    wav_bytes = _make_test_wav(duration_sec=1.0)
    req = _make_mock_request(client_ip="203.0.113.50")

    # Call 1: OK
    res1 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="s1",
        db=db_session,
    )
    assert res1.error_code is None
    assert stt_calls == 1

    # Call 2: OK
    res2 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="s2",
        db=db_session,
    )
    assert res2.error_code is None
    assert stt_calls == 2

    # Call 3: Blocked by ip_window
    res3 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="s3",
        db=db_session,
    )
    assert res3.error_code == "demo_limit"
    assert res3.limit_reason == "ip_window"
    assert res3.limit_counts is not None
    assert res3.limit_counts["ip_10m"] == 2
    assert res3.limit_counts["ip_10m_limit"] == 2
    # Ensure Gnani STT was NOT called on blocked request
    assert stt_calls == 2


def test_session_cap_limit_reason(db_session, monkeypatch):
    """When per-session cap triggers, limit_reason is 'session_cap'."""
    monkeypatch.setattr(settings, "DEMO_LIMITS", "on")
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 50)

    stt_calls = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal stt_calls
        stt_calls += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    wav_bytes = _make_test_wav(duration_sec=1.0)
    req1 = _make_mock_request(client_ip="203.0.113.51")
    req2 = _make_mock_request(client_ip="203.0.113.52")

    # Turn 1
    voice_turn(
        request=req1,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_unique_99",
        db=db_session,
    )
    # Turn 2
    voice_turn(
        request=req2,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_unique_99",
        db=db_session,
    )
    assert stt_calls == 2

    # Turn 3: Blocked by session_cap
    res3 = voice_turn(
        request=req1,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_unique_99",
        db=db_session,
    )
    assert res3.error_code == "demo_limit"
    assert res3.limit_reason == "session_cap"
    assert res3.limit_counts["session"] == 2
    assert res3.limit_counts["session_limit"] == 2
    assert stt_calls == 2


def test_reserve_and_daily_cap_limit_reason(db_session, monkeypatch):
    """When daily calls approach reserve threshold, limit_reason is 'reserve'; at daily_cap, 'daily_cap'."""
    monkeypatch.setattr(settings, "DEMO_LIMITS", "on")
    monkeypatch.setattr(settings, "GNANI_DAILY_CAP", 100)
    monkeypatch.setattr(settings, "GNANI_MAX_CALLS", 100)
    monkeypatch.setattr(settings, "GNANI_RESERVE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 50)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 50)

    # Seed 90 usage records (reaches 100 - 10 = 90 reserve threshold)
    for _ in range(90):
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True))
    db_session.commit()

    wav_bytes = _make_test_wav(duration_sec=1.0)
    req = _make_mock_request(client_ip="203.0.113.55")

    res_reserve = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_res",
        db=db_session,
    )
    assert res_reserve.error_code == "demo_limit"
    assert res_reserve.limit_reason == "reserve"
    assert res_reserve.limit_counts["daily"] == 90
    assert res_reserve.limit_counts["reserve"] == 10

    # Seed 10 more to hit daily_cap
    for _ in range(10):
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True))
    db_session.commit()

    res_cap = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_cap",
        db=db_session,
    )
    assert res_cap.error_code == "demo_limit"
    assert res_cap.limit_reason == "daily_cap"
    assert res_cap.limit_counts["daily"] == 100


def test_blocked_and_quality_gate_turns_do_not_increment_counters(db_session, monkeypatch):
    """Quality gate failures and blocked requests must NEVER count toward rate limits or call Gnani."""
    monkeypatch.setattr(settings, "DEMO_LIMITS", "on")
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 3)

    stt_called = False

    def stub_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "hello", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    # 1. Quality gate failure (too quiet - pure silence)
    silent_wav = _make_test_wav(duration_sec=1.0, amplitude=0.0)
    req = _make_mock_request(client_ip="203.0.113.60")

    res_gate = voice_turn(
        request=req,
        audio=_create_dummy_upload(silent_wav),
        language="en",
        session_id="sess_gate",
        db=db_session,
    )
    assert res_gate.error_code in ("too_quiet", "no_speech")
    assert stt_called is False

    # Verify IP and session counters remain 0
    status = credit_protection.get_limits_status(db=db_session, client_ip="203.0.113.60")
    assert status["ip_counts_10m"].get("203.0.113.60", 0) == 0
    assert status["session_counts"].get("sess_gate", 0) == 0


def test_demo_limits_off_allows_local_development_turns(db_session, monkeypatch):
    """When DEMO_LIMITS=off (or request from localhost), 20 turns run locally without being blocked."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "DEMO_LIMITS", "off")
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 3)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 3)

    stt_count = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal stt_count
        stt_count += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    wav_bytes = _make_test_wav(duration_sec=1.0)
    req = _make_mock_request(client_ip="127.0.0.1")

    # Run 20 consecutive turns on localhost
    for i in range(20):
        res = voice_turn(
            request=req,
            audio=_create_dummy_upload(wav_bytes),
            language="en",
            session_id="local_dev_session",
            db=db_session,
        )
        assert res.error_code is None
        # On turn 4+, it would have triggered ip_window / session_cap, so simulated limit_reason is reported in dev
        if i >= 3:
            assert res.limit_reason in ("ip_window", "session_cap")
            assert res.limit_counts is not None

    assert stt_count == 20


def test_owner_key_bypasses_limits_but_hard_cap_blocks(db_session, monkeypatch):
    """Owner key skips per-IP, per-session, and reserve limits, but GNANI_MAX_CALLS hard cap blocks."""
    monkeypatch.setattr(settings, "OWNER_KEY", "super_secret_owner_key")
    monkeypatch.setattr(settings, "DEMO_LIMITS", "on")
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 1)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 1)
    monkeypatch.setattr(settings, "GNANI_MAX_CALLS", 10)
    monkeypatch.setattr(settings, "GNANI_DAILY_CAP", 10)

    stt_count = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal stt_count
        stt_count += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    wav_bytes = _make_test_wav(duration_sec=1.0)
    owner_req = _make_mock_request(client_ip="203.0.113.88", owner_key="super_secret_owner_key")

    # Turns 1 & 2 succeed with owner key even though RATE_LIMIT_VOICE_10MIN=1 and SESSION_VOICE_CAP=1
    res1 = voice_turn(
        request=owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_sess",
        db=db_session,
    )
    assert res1.error_code is None

    res2 = voice_turn(
        request=owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_sess",
        db=db_session,
    )
    assert res2.error_code is None
    assert stt_count == 2

    # Now seed DB up to GNANI_MAX_CALLS = 10
    for _ in range(10):
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True))
    db_session.commit()

    # Turn 3: Hard cap is reached, owner is BLOCKED
    res3 = voice_turn(
        request=owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_sess",
        db=db_session,
    )
    assert res3.error_code == "demo_limit"
    assert res3.limit_reason == "daily_cap"
    assert stt_count == 2  # No new call made


def test_single_language_limit_messages(monkeypatch):
    """Telugu and English limit messages must be single-language without slashes."""
    monkeypatch.setattr(settings, "DEMO_VIDEO_URL", "")

    te_msg = credit_protection.get_demo_limit_message("te")
    en_msg = credit_protection.get_demo_limit_message("en")

    # Telugu message must not contain slash or english text
    assert "/" not in te_msg
    assert "Voice demo limit" not in te_msg
    assert "పరిమితి" in te_msg

    # English message must not contain slash or telugu text
    assert "/" not in en_msg
    assert "పరిమితి" not in en_msg
    assert "Voice demo limit" in en_msg


def test_dev_limits_and_reset_endpoints(db_session, monkeypatch):
    """GET /dev/limits and POST /dev/reset-limits work when DEV_ENDPOINTS=true."""
    from backend.app.routers.turn_router import dev_limits, dev_reset_limits

    monkeypatch.setattr(settings, "DEV_ENDPOINTS", True)
    req = _make_mock_request(client_ip="127.0.0.1")

    # 1. GET /dev/limits
    data = dev_limits(request=req, db=db_session)
    assert "real_calls_today" in data
    assert "daily_cap" in data
    assert "hard_cap" in data
    assert "session_voice_cap" in data

    # 2. Record a simulated in-memory voice turn
    credit_protection.record_voice_turn("198.51.100.99", "sess_dev_test")
    res_after = dev_limits(request=req, db=db_session)
    assert res_after["session_counts"].get("sess_dev_test") == 1

    # 3. POST /dev/reset-limits
    res_post = dev_reset_limits()
    assert res_post["status"] == "ok"

    # 4. Verify cleared
    res_cleared = dev_limits(request=req, db=db_session)
    assert res_cleared["session_counts"].get("sess_dev_test") is None

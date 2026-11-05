"""Tests for Credit Protection and Rate Limiting for Public Link (P1-6).

Hard rules:
- Zero real Gnani calls (all STT and TTS are stubbed).
- Secrets in .env only.
- Languages: Telugu, English, Mix. No Hindi.
- No fake/mock voice data in app code.
"""

from datetime import datetime, timezone
import io
import math
import struct
import wave
from fastapi import UploadFile
import pytest
from starlette.requests import Request

from backend.app.config import settings
from backend.app.models import GnaniUsage, Token
from backend.app.routers.turn_router import get_usage, text_turn, voice_turn
from backend.app.schemas import TextTurnRequest
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


def _make_mock_request(client_ip: str = "127.0.0.1", owner_key: str | None = None, forwarded_for: str | None = None) -> Request:
    headers = []
    if owner_key is not None:
        headers.append((b"x-owner-key", owner_key.encode("latin-1")))
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("latin-1")))

    scope = {
        "type": "http",
        "client": (client_ip, 12345),
        "headers": headers,
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def clean_credit_limits():
    """Ensure in-memory rate limiting state is reset before and after every test."""
    credit_protection.reset_limits()
    yield
    credit_protection.reset_limits()


def test_ip_ten_minute_limit_blocks_third_voice_turn(db_session, monkeypatch):
    """With small caps set in env (limit=2), third voice turn from same IP returns demo_limit with zero Gnani call."""
    credit_calls = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal credit_calls
        credit_calls += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 2)
    monkeypatch.setattr(settings, "DEMO_VIDEO_URL", "https://example.com/demo.mp4")

    wav_bytes = _make_test_wav(duration_sec=1.0)
    req = _make_mock_request(client_ip="203.0.113.19")

    # Turn 1: Succeeds
    res1 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_ip_1",
        db=db_session,
    )
    assert res1.error_code is None
    assert credit_calls == 1

    # Turn 2: Succeeds
    res2 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_ip_2",
        db=db_session,
    )
    assert res2.error_code is None
    assert credit_calls == 2

    # Turn 3: Blocked by 10-min IP limit
    res3 = voice_turn(
        request=req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="sess_ip_3",
        db=db_session,
    )
    assert res3.error_code == "demo_limit"
    assert "Voice demo limit reached for now. Please watch the demo video or try typing." in res3.reply_text
    assert "https://example.com/demo.mp4" in res3.reply_text
    assert res3.reply_audio_base64 is None
    # Crucial: NO third Gnani call made!
    assert credit_calls == 2


def test_per_session_voice_cap(db_session, monkeypatch):
    """Session cap blocks turn when session limit is reached, even from different IPs."""
    credit_calls = 0

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal credit_calls
        credit_calls += 1
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 10)

    wav_bytes = _make_test_wav(duration_sec=1.0)

    # Turn 1: IP A, session S1
    req_a = _make_mock_request(client_ip="198.51.100.1")
    res1 = voice_turn(
        request=req_a,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="shared_sess",
        db=db_session,
    )
    assert res1.error_code is None
    assert credit_calls == 1

    # Turn 2: IP B, same session S1
    req_b = _make_mock_request(client_ip="198.51.100.2")
    res2 = voice_turn(
        request=req_b,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="shared_sess",
        db=db_session,
    )
    assert res2.error_code is None
    assert credit_calls == 2

    # Turn 3: IP C, same session S1 -> blocked by session cap
    req_c = _make_mock_request(client_ip="198.51.100.3")
    res3 = voice_turn(
        request=req_c,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="shared_sess",
        db=db_session,
    )
    assert res3.error_code == "demo_limit"
    assert credit_calls == 2


def test_reserve_blocks_strangers_when_few_remain(db_session, monkeypatch):
    """Real calls are blocked when fewer than GNANI_RESERVE remain, unless X-Owner-Key matches OWNER_KEY."""
    stt_called = False

    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(settings, "GNANI_DAILY_CAP", 100)
    monkeypatch.setattr(settings, "GNANI_RESERVE", 30)
    monkeypatch.setattr(settings, "OWNER_KEY", "super_secret_owner_key_42")

    # Simulate 70 calls already made today (100 - 30 = 70 threshold reached)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(70):
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True, created_at=today_start))
    db_session.commit()

    wav_bytes = _make_test_wav(duration_sec=1.0)

    # 1. Non-owner request (stranger) is blocked
    stranger_req = _make_mock_request(client_ip="192.0.2.1")
    res_stranger = voice_turn(
        request=stranger_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="stranger_sess",
        db=db_session,
    )
    assert res_stranger.error_code == "demo_limit"
    assert stt_called is False

    # 2. Invalid owner key is blocked
    bad_owner_req = _make_mock_request(client_ip="192.0.2.1", owner_key="wrong_key")
    res_bad = voice_turn(
        request=bad_owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="bad_owner_sess",
        db=db_session,
    )
    assert res_bad.error_code == "demo_limit"
    assert stt_called is False

    # 3. Valid owner request bypasses reserve
    valid_owner_req = _make_mock_request(client_ip="192.0.2.1", owner_key="super_secret_owner_key_42")
    res_owner = voice_turn(
        request=valid_owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_sess",
        db=db_session,
    )
    assert res_owner.error_code is None
    assert stt_called is True


def test_owner_bypasses_ip_and_session_limits(db_session, monkeypatch):
    """Owner key allows turns even when IP or session limit would block strangers."""
    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 1)
    monkeypatch.setattr(settings, "SESSION_VOICE_CAP", 1)
    monkeypatch.setattr(settings, "OWNER_KEY", "valid_owner_pass")

    wav_bytes = _make_test_wav(duration_sec=1.0)
    owner_req = _make_mock_request(client_ip="10.0.0.5", owner_key="valid_owner_pass")

    # Turn 1
    res1 = voice_turn(
        request=owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_fixed_sess",
        db=db_session,
    )
    assert res1.error_code is None

    # Turn 2: Exceeds 1-turn limit, but owner key bypasses it
    res2 = voice_turn(
        request=owner_req,
        audio=_create_dummy_upload(wav_bytes),
        language="en",
        session_id="owner_fixed_sess",
        db=db_session,
    )
    assert res2.error_code is None


def test_typed_requests_keep_working_under_cap_without_calling_timbre(db_session, monkeypatch):
    """When a cap is reached, typed requests keep working: text reply is returned, audio only from cache."""
    tts_called = False

    def stub_tts(text, lang, *args, **kwargs):
        nonlocal tts_called
        tts_called = True
        return b"RIFFstub"

    monkeypatch.setattr(gnani, "tts", stub_tts)
    monkeypatch.setattr(settings, "RATE_LIMIT_VOICE_10MIN", 1)

    # Exceed IP limit
    req = _make_mock_request(client_ip="10.20.30.40")
    credit_protection.record_voice_turn("10.20.30.40", "sess_text_test")

    # Send typed turn
    payload = TextTurnRequest(
        text="I need a token for tomorrow",
        language="en",
        session_id="sess_text_test",
    )
    res = text_turn(payload=payload, request=req, db=db_session)

    # Token booked, text reply present
    assert res.token is not None
    assert "token" in res.reply_text.lower()
    # Typed request never called live Timbre TTS because cap is reached
    assert tts_called is False


def test_usage_endpoint_reports_limit_and_reserve(db_session, monkeypatch):
    """GET /usage returns real_calls_today, limit from GNANI_DAILY_CAP, and reserve from GNANI_RESERVE."""
    monkeypatch.setattr(settings, "GNANI_DAILY_CAP", 150)
    monkeypatch.setattr(settings, "GNANI_RESERVE", 40)

    # Add 3 real calls
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(3):
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True, created_at=today_start))
    db_session.commit()

    usage = get_usage(db=db_session)
    assert usage.real_calls_today == 3
    assert usage.limit == 150
    assert usage.reserve == 40


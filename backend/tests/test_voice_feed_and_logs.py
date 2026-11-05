"""Tests for Voice Activity Feed and Audit Logs (P1-4).

Tests:
1. Successful voice turn saves a voice_log and appears in /voice-logs with human-readable language (Telugu/English).
2. Failed turns (quality gate: too_quiet, no_speech; Gnani errors: rate_limit, etc.) appear in /voice-logs with ok=False and error_code.
3. Reset demo does NOT delete voice logs (leaves feed intact).
4. Clear voice log deletes voice logs without affecting patient tokens.
5. GET /voice-logs returns newest first with a maximum of 20 items.
"""

import io
import math
import struct
import wave
from fastapi import UploadFile
import pytest

from backend.app.models import Token, VoiceLog
from backend.app.routers.turn_router import clear_voice_logs, get_voice_logs, voice_turn
from backend.app.services import gnani, queue_service


def _make_test_wav(duration_sec: float = 1.0, amplitude: float = 0.2, freq: float = 440.0, sample_rate: int = 16000) -> bytes:
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


def test_successful_voice_turn_appears_in_voice_logs(db_session, monkeypatch):
    """A successful voice turn is recorded and returned by /voice-logs with human language name."""
    # Stub STT
    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        return {"transcript": "I need a token for tomorrow", "language": "en-IN"}

    monkeypatch.setattr(gnani, "stt", stub_stt)

    # Valid 1-second audio tone
    wav_bytes = _make_test_wav(duration_sec=1.0, amplitude=0.3)
    upload = _create_dummy_upload(wav_bytes)

    res = voice_turn(
        audio=upload,
        language="en",
        session_id="feed_sess_1",
        token_id=None,
        noise_label="quiet",
        clean=True,
        db=db_session,
    )

    assert res.token is not None
    assert res.token.number is not None

    logs = get_voice_logs(limit=20, db=db_session)
    assert len(logs) >= 1
    newest = logs[0]
    assert newest.transcript == "I need a token for tomorrow"
    assert newest.detected_language == "English"  # Human readable, not "en-IN"
    assert newest.intent == "BOOK"
    assert newest.token_number == res.token.number
    assert newest.ok is True
    assert newest.error is None


def test_failed_quality_gate_turn_appears_in_voice_logs(db_session, monkeypatch):
    """Failed quality gates (e.g. too_quiet, too_short, corrupt_file) are logged with error_code."""
    # Create very quiet audio (< 0.005 RMS)
    quiet_bytes = _make_test_wav(duration_sec=1.0, amplitude=0.0001)
    upload = _create_dummy_upload(quiet_bytes)

    res = voice_turn(
        audio=upload,
        language="te",
        session_id="feed_sess_gate",
        token_id=None,
        noise_label="quiet",
        clean=False,
        db=db_session,
    )

    assert res.intent == "UNKNOWN"
    assert res.error_code in ("too_quiet", "no_speech")

    logs = get_voice_logs(limit=20, db=db_session)
    assert len(logs) >= 1
    newest = logs[0]
    assert newest.ok is False
    assert newest.error in ("too_quiet", "no_speech")
    assert newest.detected_language == "Telugu"


def test_failed_gnani_error_turn_appears_in_voice_logs(db_session, monkeypatch):
    """Gnani errors (429, timeout, network) are logged with error_code."""
    def stub_stt_fail(wav_bytes, user_lang="te", *args, **kwargs):
        raise gnani.GnaniRateLimitError("HTTP 429 Rate limit exceeded")

    monkeypatch.setattr(gnani, "stt", stub_stt_fail)

    wav_bytes = _make_test_wav(duration_sec=1.0, amplitude=0.3)
    upload = _create_dummy_upload(wav_bytes)

    res = voice_turn(
        audio=upload,
        language="en",
        session_id="feed_sess_fail",
        token_id=None,
        noise_label="street",
        clean=True,
        db=db_session,
    )

    assert res.intent == "ERROR"

    logs = get_voice_logs(limit=20, db=db_session)
    assert len(logs) >= 1
    newest = logs[0]
    assert newest.ok is False
    assert newest.error == "rate_limit"


def test_reset_demo_preserves_voice_logs(db_session, monkeypatch):
    """Reset demo wipes patient tokens but preserves voice activity logs intact."""
    # Seed a token
    tok = queue_service.book(db_session, day="today", language="te-IN")

    # Add a voice log referencing that token
    vlog = VoiceLog(
        token_id=tok.id,
        transcript="Test voice interaction",
        detected_language="Telugu",
        intent="BOOK",
        ok=True,
    )
    db_session.add(vlog)
    db_session.commit()

    # Confirm log exists
    initial_logs = get_voice_logs(limit=20, db=db_session)
    assert len(initial_logs) == 1

    # Execute reset_demo
    queue_service.reset_demo(db_session)

    # Tokens must be cleared
    assert db_session.query(Token).count() == 0

    # Voice logs must remain intact!
    logs_after_reset = get_voice_logs(limit=20, db=db_session)
    assert len(logs_after_reset) == 1
    assert logs_after_reset[0].transcript == "Test voice interaction"


def test_clear_voice_logs_clears_only_logs(db_session):
    """Clear voice logs deletes only voice activity logs, leaving patient queue intact."""
    tok = queue_service.book(db_session, day="today", language="en-IN")
    vlog = VoiceLog(
        token_id=tok.id,
        transcript="Test clear log",
        detected_language="English",
        intent="STATUS",
        ok=True,
    )
    db_session.add(vlog)
    db_session.commit()

    # Clear voice logs
    clear_voice_logs(db=db_session)

    # Voice logs must be 0
    assert len(get_voice_logs(limit=20, db=db_session)) == 0

    # Token must still be intact
    assert db_session.query(Token).filter(Token.id == tok.id).first() is not None


def test_voice_logs_maximum_20_and_newest_first(db_session):
    """GET /voice-logs returns at most 20 items ordered newest first."""
    for i in range(25):
        vlog = VoiceLog(
            transcript=f"Turn message {i}",
            detected_language="te",
            intent="BOOK",
            ok=True,
        )
        db_session.add(vlog)
    db_session.commit()

    logs = get_voice_logs(limit=20, db=db_session)
    assert len(logs) == 20
    # Newest item first (Turn message 24)
    assert logs[0].transcript == "Turn message 24"
    assert logs[19].transcript == "Turn message 5"

"""Pytest suite for audio processing, cached prompts, and voice/text interaction turns."""

import base64
import io
import math
import struct
import wave
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.models import Token, VoiceLog
from backend.app.routers.turn_router import text_turn
from backend.app.schemas import TextTurnRequest
from backend.app.services import audio, queue_service

def make_test_wav(
    duration_sec: float = 0.5,
    freq: float = 330.0,
    amplitude: float = 0.4,
    sample_rate: int = 16000,
) -> bytes:
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

# Test database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 1. Audio Conversion Unit Tests & Quality Gates ---
def test_audio_conversion_valid():
    sample_wav = make_test_wav(duration_sec=1.0, amplitude=0.5)
    converted = audio.process_audio_with_gates(sample_wav, filename="test.wav")
    assert len(converted) > 0
    assert converted.startswith(b"RIFF")


def test_audio_conversion_rejects_empty():
    with pytest.raises(audio.AudioQualityGateError) as exc_info:
        audio.process_audio_with_gates(b"", filename="empty.wav")
    assert exc_info.value.error_code == "no_speech"


def test_quality_gate_rejects_too_short():
    short_wav = make_test_wav(duration_sec=0.3, amplitude=0.5)
    with pytest.raises(audio.AudioQualityGateError) as exc_info:
        audio.process_audio_with_gates(short_wav, filename="short.wav")
    assert exc_info.value.error_code == "too_short"


def test_quality_gate_rejects_over_30s():
    long_wav = make_test_wav(duration_sec=31.0, amplitude=0.5)
    with pytest.raises(audio.AudioQualityGateError) as exc_info:
        audio.process_audio_with_gates(long_wav, filename="long.wav")
    assert exc_info.value.error_code == "too_long"


def test_quality_gate_silence_detected_as_no_speech():
    # 2 seconds of pure digital silence
    silent_wav = make_test_wav(duration_sec=2.0, amplitude=0.0)
    with pytest.raises(audio.AudioQualityGateError) as exc_info:
        audio.process_audio_with_gates(silent_wav, filename="silence.wav")
    assert exc_info.value.error_code == "no_speech"


def test_quality_gate_too_quiet():
    # 1.5 seconds of faint whisper below speech threshold
    quiet_wav = make_test_wav(duration_sec=1.5, amplitude=0.003)
    with pytest.raises(audio.AudioQualityGateError) as exc_info:
        audio.process_audio_with_gates(quiet_wav, filename="quiet.wav")
    assert exc_info.value.error_code in ("too_quiet", "no_speech")


# --- 2. Cached Audio Loader Tests ---
def test_cached_audio_retrieval():
    greeting_audio = audio.get_cached_audio("greeting_en") or audio.get_cached_audio("cancelled_en")
    assert greeting_audio is not None
    assert len(greeting_audio) > 0
    assert greeting_audio.startswith(b"RIFF")

    missing = audio.get_cached_audio("non_existent_cache_key")
    assert missing is None


# --- 3. Text Turn Service & Flow Tests ---
def test_text_turn_booking_telugu(db_session):
    req = TextTurnRequest(
        text="Naaku repu token kavali",
        language="te",
        session_id="test_sess_1",
    )
    res = text_turn(payload=req, db=db_session)
    assert res.intent == "BOOK"
    assert res.token is not None
    assert res.token.number == 1
    assert "ఒకటి" in res.reply_text
    assert res.pending_confirm is False
    assert res.error is None
    # Audio returned as base64
    audio_bytes = base64.b64decode(res.reply_audio_base64)
    assert audio_bytes.startswith(b"RIFF")

    # Check VoiceLog saved
    vlog = db_session.query(VoiceLog).first()
    assert vlog is not None
    assert vlog.intent == "BOOK"
    assert vlog.token_id == res.token.id


def test_text_turn_status_check(db_session):
    # Book a token first
    tok = queue_service.book(db_session, day="today", language="te-IN")

    req = TextTurnRequest(
        text="What is the status of my token number?",
        language="en",
        session_id="test_sess_2",
        token_id=tok.id,
    )
    res = text_turn(payload=req, db=db_session)
    assert res.intent == "STATUS"
    assert res.token is not None
    assert res.token.id == tok.id
    assert "token number" in res.reply_text.lower()
    assert res.error is None


def test_text_turn_cancel_confirmation_flow(db_session):
    tok = queue_service.book(db_session, day="today", language="en-IN")
    sess_id = "test_sess_cancel"

    # Turn 1: User says cancel -> asks for confirmation
    req1 = TextTurnRequest(
        text="Please cancel my token",
        language="en",
        session_id=sess_id,
        token_id=tok.id,
    )
    res1 = text_turn(payload=req1, db=db_session)
    assert res1.intent == "CANCEL"
    assert res1.pending_confirm is True
    assert "sure you want to cancel" in res1.reply_text.lower()

    # Turn 2: User says YES -> cancels token
    req2 = TextTurnRequest(
        text="Yes",
        language="en",
        session_id=sess_id,
    )
    res2 = text_turn(payload=req2, db=db_session)
    assert res2.pending_confirm is False
    assert "cancelled successfully" in res2.reply_text.lower()

    db_session.refresh(tok)
    assert tok.status == "cancelled"


def test_text_turn_cancel_aborted_flow(db_session):
    tok = queue_service.book(db_session, day="today", language="te-IN")
    sess_id = "test_sess_abort"

    # Turn 1: User requests cancel
    req1 = TextTurnRequest(
        text="Cancel cheyandi",
        language="te",
        session_id=sess_id,
        token_id=tok.id,
    )
    res1 = text_turn(payload=req1, db=db_session)
    assert res1.pending_confirm is True

    # Turn 2: User says NO -> aborts
    req2 = TextTurnRequest(
        text="Vaddu",
        language="te",
        session_id=sess_id,
    )
    res2 = text_turn(payload=req2, db=db_session)
    assert res2.pending_confirm is False
    assert "ఆపివేయబడింది" in res2.reply_text

    db_session.refresh(tok)
    assert tok.status == "waiting"


def test_text_turn_empty_input_says_again(db_session):
    req = TextTurnRequest(
        text="",
        language="te",
        session_id="test_sess_empty",
    )
    res = text_turn(payload=req, db=db_session)
    assert res.intent == "UNKNOWN"
    assert "మళ్లీ చెప్పండి" in res.reply_text
    assert res.error is None


# --- 4. Quality Gate Voice Turn Endpoint & Debug Audio Tests ---
def test_voice_turn_gate_silent_clip_returns_200_no_gnani(db_session):
    import io
    from fastapi import UploadFile
    from backend.app.routers.turn_router import voice_turn

    # Generate 1.5s of digital silence
    silent_wav = make_test_wav(duration_sec=1.5, amplitude=0.0)
    upload = UploadFile(file=io.BytesIO(silent_wav), filename="silent.wav")

    # Call voice_turn directly
    res = voice_turn(
        audio=upload,
        language="te",
        session_id="test_silent_gate",
        db=db_session,
    )

    assert res.intent == "UNKNOWN"
    assert res.error_code == "no_speech"
    assert "ఎటువంటి మాటలు వినిపించలేదు" in res.reply_text
    assert len(res.reply_audio_base64) > 0


def test_debug_audio_saving():
    from backend.app.config import settings

    old_debug = settings.DEBUG_SAVE_AUDIO
    try:
        settings.DEBUG_SAVE_AUDIO = True
        audio.clear_debug_audio_dir()

        test_clip = make_test_wav(duration_sec=1.0, amplitude=0.4)
        audio.process_audio_with_gates(test_clip, filename="debug_test.wav")

        saved_files = list(audio.DEBUG_AUDIO_DIR.glob("*"))
        assert len(saved_files) == 2  # 1 raw and 1 cleaned
        assert any("raw" in f.name for f in saved_files)
        assert any("cleaned" in f.name for f in saved_files)
    finally:
        audio.clear_debug_audio_dir()
        settings.DEBUG_SAVE_AUDIO = old_debug





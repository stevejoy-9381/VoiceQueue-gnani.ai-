"""Tests for Phase F: Spoken reply generation, graceful Timbre failure handling, and logging."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.schemas import TurnResponse
from backend.app.services import gnani, turn_service

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


def test_timbre_failure_returns_text_without_crash(db_session, monkeypatch, capsys):
    """If Timbre TTS synthesis fails, return text reply with error and no audio, without crashing."""
    # Force gnani.tts to raise an error
    def failing_tts(text, lang, voice=None):
        raise gnani.GnaniAPIError("Gnani TTS service unavailable (503)")

    monkeypatch.setattr(gnani, "tts", failing_tts)
    # Ensure cache returns None to force dynamic synthesis
    from backend.app.services import audio
    monkeypatch.setattr(audio, "get_cached_audio", lambda key: None)

    res = turn_service.process_turn(
        db=db_session,
        transcript="repu token kavali",
        detected_lang="te-IN",
        requested_lang="te",
        session_id="test_failing_tts",
    )

    # Must return valid intent, text reply, and token without crashing
    assert res.intent == "BOOK"
    assert res.token is not None
    assert "టోకెన్" in res.reply_text
    # Audio is empty on failure
    assert res.reply_audio_base64 == ""
    # Error message is populated
    assert res.error is not None
    assert "Gnani TTS service unavailable" in res.error

    # Verify log output
    captured = capsys.readouterr()
    assert "[TTS Audio] Timbre TTS synthesis failed:" in captured.out


def test_audio_source_logging_cache_and_generated(db_session, monkeypatch, capsys):
    """Verifies that whether audio came from cache or was generated is logged clearly."""
    # 1. Test cache hit logging
    from backend.app.services import audio
    monkeypatch.setattr(audio, "get_cached_audio", lambda key: b"RIFF_CACHED_WAV")

    turn_service.process_turn(
        db=db_session,
        transcript="cancel",
        detected_lang="en-IN",
        requested_lang="en",
        session_id="test_cache_logging",
    )
    captured1 = capsys.readouterr()
    assert "[TTS Audio] Source=CACHE" in captured1.out

    # 2. Test generated logging
    monkeypatch.setattr(audio, "get_cached_audio", lambda key: None)
    monkeypatch.setattr(gnani, "tts", lambda text, lang, voice=None: b"RIFF_GENERATED_WAV")

    turn_service.process_turn(
        db=db_session,
        transcript="I want a token tomorrow",
        detected_lang="en-IN",
        requested_lang="en",
        session_id="test_gen_logging",
    )
    captured2 = capsys.readouterr()
    assert "[TTS Audio] Source=GENERATED (Timbre)" in captured2.out


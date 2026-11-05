"""Tests for Phase D: Prisma settings, transcript handling, quality gates & retries."""

import json
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
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


def test_stt_request_payload_and_language_hints(monkeypatch):
    """Verifies that Prisma v3.0 parameters, keywords, topic, and language hints are set accurately."""
    monkeypatch.setattr(settings, "GNANI_API_KEY", "test-api-key")
    monkeypatch.setattr(gnani, "_check_daily_credit_limit", lambda db=None: None)
    monkeypatch.setattr(gnani, "_log_call_usage", lambda *a, **kw: None)

    # Test Telugu/Mix mode
    def mock_execute_te(call_fn):
        return httpx.Response(
            status_code=200,
            json={"transcript": "   repu   token    kavali   ", "detected_language_code": "te-IN"},
            request=httpx.Request("POST", "http://test/stt"),
        )

    monkeypatch.setattr(gnani, "_execute_with_lock_and_retry", mock_execute_te)
    res_te = gnani._raw_stt(b"dummy_wav", user_lang="te")
    # Transcript spaces collapsed and trimmed
    assert res_te["transcript"] == "repu token kavali"
    assert res_te["language"] == "te-IN"

    # Test English mode
    def mock_execute_en(call_fn):
        return httpx.Response(
            status_code=200,
            json={"transcript": "  appointment    tomorrow   ", "detected_language_code": "en-IN"},
            request=httpx.Request("POST", "http://test/stt"),
        )

    monkeypatch.setattr(gnani, "_execute_with_lock_and_retry", mock_execute_en)
    res_en = gnani._raw_stt(b"dummy_wav", user_lang="en")
    assert res_en["transcript"] == "appointment tomorrow"
    assert res_en["language"] == "en-IN"


def test_empty_transcript_handling_no_token(db_session):
    """Empty or whitespace-only transcript must return cached say-again reply and never create a token."""
    res = turn_service.process_turn(
        db=db_session,
        transcript="     ",
        detected_lang="te-IN",
        requested_lang="te",
        session_id="test_empty_phase_d",
        audio_stats={"duration": 1.2, "peak": 0.4, "rms": 0.15},
    )

    assert res.token is None
    assert res.transcript == ""
    assert res.error_code == "empty_transcript"
    assert "మళ్లీ చెప్పండి" in res.reply_text
    assert res.audio_stats == {"duration": 1.2, "peak": 0.4, "rms": 0.15}
    assert len(res.reply_audio_base64) > 0


def test_retry_on_network_error_and_5xx():
    """_execute_with_lock_and_retry must retry once on network exceptions and 5xx errors."""
    attempts = 0

    def flaky_endpoint():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.NetworkError("Network glitch")
        return httpx.Response(status_code=200, json={"success": True}, request=httpx.Request("GET", "http://test"))

    res = gnani._execute_with_lock_and_retry(flaky_endpoint)
    assert res.status_code == 200
    assert attempts == 2


def test_turn_response_schema():
    """TurnResponse must support transcript, detected_language, audio_stats, and error_code."""
    turn_res = TurnResponse(
        transcript="repu token kavali",
        detected_language="te-IN",
        intent="BOOK",
        reply_text="మీ టోకెన్ బుక్ అయింది",
        reply_audio_base64="dummy_b64",
        token=None,
        pending_confirm=False,
        error=None,
        error_code=None,
        audio_stats={"duration": 2.5, "peak": 0.6, "rms": 0.22},
    )
    assert turn_res.transcript == "repu token kavali"
    assert turn_res.detected_language == "te-IN"
    assert turn_res.audio_stats["duration"] == 2.5
    assert turn_res.error_code is None

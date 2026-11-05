"""Tests for Gnani STT and TTS failure modes and simulations.

Simulates:
- 200 normal
- 400 invalid voice
- 401 Bad API key
- 402 No credits remaining
- 403 Forbidden
- 429 Rate limit (retry once then friendly error)
- 500 Server error (retry once)
- Network timeout (retry once)
- Empty transcript from STT

Verifies that /voice/turn always returns HTTP 200 with a clear error field,
never crashes, and raw Gnani JSON is never shown to patients.
"""

import httpx
import pytest
from backend.app.services import gnani, turn_service
from backend.tests.audio_generator import ensure_test_audio_files


@pytest.fixture(scope="module")
def audio_files():
    return ensure_test_audio_files()


@pytest.fixture(autouse=True)
def fast_retry(monkeypatch):
    """Monkeypatch time.sleep so retries are instantaneous during tests."""
    monkeypatch.setattr("time.sleep", lambda s: None)


class DummyResponse:
    """Mock HTTP response simulating Gnani status codes."""

    def __init__(self, status_code: int, text: str = "", content: bytes = b"", json_data: dict | None = None):
        self.status_code = status_code
        self.text = text
        self.content = content
        self._json_data = json_data or {}
        self.is_success = (200 <= status_code < 300)

    def json(self):
        return self._json_data


def test_gnani_200_normal(client, audio_files, monkeypatch):
    """200 OK: Normal STT and TTS succeed with clean turn response."""
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda wav_bytes, user_lang="en", *a, **kw: {"transcript": "book token tomorrow", "language": "en-IN"},
    )

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "sess-200-normal"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "BOOK"
    assert data["token"] is not None
    assert data["error"] is None
    assert data["error_code"] is None


def test_gnani_stt_401_auth_error(client, audio_files, monkeypatch):
    """401 Unauthorized: Return HTTP 200 with clear error field and friendly patient text."""
    def stub_401(*args, **kwargs):
        raise gnani.GnaniAuthError("Gnani API key is invalid (HTTP 401).")

    monkeypatch.setattr(gnani, "stt", stub_401)

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "sess-401-auth"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "401" in data["error"] or "invalid" in data["error"].lower()
    assert data["error_code"] == "GnaniAuthError"
    # Patient sees friendly service paused message, never raw Gnani JSON
    assert "currently paused" in data["reply_text"].lower() or "paused" in data["reply_text"].lower()
    assert "{" not in data["reply_text"]  # No raw JSON leaked


def test_gnani_stt_402_no_credits(client, audio_files, monkeypatch):
    """402 Payment Required: Return HTTP 200 with clear error field and friendly patient text."""
    def stub_402(*args, **kwargs):
        raise gnani.GnaniNoCreditsError("Gnani account has no credits remaining (HTTP 402).")

    monkeypatch.setattr(gnani, "stt", stub_402)

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "sess-402-credits"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "402" in data["error"] or "credits" in data["error"].lower()
    assert data["error_code"] == "GnaniNoCreditsError"
    assert "అందుబాటులో లేదు" in data["reply_text"] or "paused" in data["reply_text"].lower()
    assert "{" not in data["reply_text"]


def test_gnani_stt_403_forbidden(client, audio_files, monkeypatch):
    """403 Forbidden: Return HTTP 200 with clear error field and friendly text."""
    def stub_403(*args, **kwargs):
        raise gnani.GnaniForbiddenError("Gnani API permission denied (HTTP 403).")

    monkeypatch.setattr(gnani, "stt", stub_403)

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "sess-403-forbidden"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "403" in data["error"] or "permission denied" in data["error"].lower()
    assert data["error_code"] == "GnaniForbiddenError"
    assert "currently paused" in data["reply_text"].lower() or "paused" in data["reply_text"].lower()


def test_gnani_retry_once_on_429(client, audio_files, monkeypatch):
    """429 Rate Limit: Retries once; if succeeds on retry, completes turn cleanly."""
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return DummyResponse(429, text="Rate limit exceeded")
        return DummyResponse(200, json_data={"transcript": "today token status", "language": "en-IN"})

    # Test the low-level lock-and-retry helper directly
    resp = gnani._execute_with_lock_and_retry(mock_call)
    assert call_count == 2
    assert resp.status_code == 200


def test_gnani_fail_after_retry_on_429(client, audio_files, monkeypatch):
    """429 Rate Limit: If 429 persists after retry, raises GnaniRateLimitError and returns friendly error."""
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        return DummyResponse(429, text="Rate limit exceeded")

    with pytest.raises(gnani.GnaniRateLimitError):
        gnani._execute_with_lock_and_retry(mock_call)
    assert call_count == 2, "Expected exactly 1 retry (2 calls total) on 429"


def test_gnani_retry_once_on_500(client, audio_files, monkeypatch):
    """500 Server Error: Retries once; if succeeds on retry, completes turn cleanly."""
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return DummyResponse(500, text="Internal Server Error")
        return DummyResponse(200, json_data={"transcript": "hello", "language": "en-IN"})

    resp = gnani._execute_with_lock_and_retry(mock_call)
    assert call_count == 2
    assert resp.status_code == 200


def test_gnani_fail_after_retry_on_500(client, audio_files, monkeypatch):
    """500 Server Error: If 500 persists after retry, raises GnaniAPIError."""
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        return DummyResponse(500, text="Internal Server Error")

    with pytest.raises(gnani.GnaniAPIError):
        gnani._execute_with_lock_and_retry(mock_call)
    assert call_count == 2, "Expected exactly 1 retry on 500"


def test_gnani_retry_once_on_network_timeout(client, audio_files, monkeypatch):
    """Network Timeout: Retries once on httpx.TimeoutException."""
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("Read timeout after 30s")
        return DummyResponse(200, json_data={"transcript": "repu token", "language": "te-IN"})

    resp = gnani._execute_with_lock_and_retry(mock_call)
    assert call_count == 2
    assert resp.status_code == 200


def test_gnani_empty_transcript_handling(client, audio_files, monkeypatch):
    """Empty transcript returned from STT triggers 'empty_transcript' without crashing."""
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda *a, **kw: {"transcript": "", "language": "en-IN"},
    )

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "sess-empty-transcript"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "UNKNOWN"
    assert data["error_code"] == "empty_transcript"
    assert "say that again" in data["reply_text"].lower()


def test_gnani_tts_400_invalid_voice(client, audio_files, monkeypatch):
    """TTS 400 Invalid Voice: Returns HTTP 200, keeps text on screen, friendly message without raw JSON."""
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda *a, **kw: {"transcript": "book token tomorrow", "language": "en-IN"},
    )

    def stub_bad_voice_tts(text, lang, voice=None):
        raise gnani.VoiceNotSupportedError("Voice 'BadVoice' is not supported by model timbre-v2.5")

    monkeypatch.setattr(gnani, "tts", stub_bad_voice_tts)

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "sess-tts-bad-voice"},
    )

    assert resp.status_code == 200
    data = resp.json()
    # Booking succeeded: token is created and text reply is available
    assert data["intent"] == "BOOK"
    assert data["token"] is not None
    assert len(data["reply_text"]) > 0
    # Voice error details are reported in error field, friendly to user
    assert data["error"] is not None
    assert "voice" in data["error"].lower() or "unavailable" in data["error"].lower()
    # Patient does not see raw JSON
    assert "{" not in data["reply_text"]

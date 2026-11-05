"""Phase T1 - Backend Configuration and Health Endpoint Tests.

Tests:
1. /health reports gnani_configured=True when GNANI_API_KEY is present, False when missing.
2. /health reports ffmpeg_found=True when ffmpeg is available, False when missing.
3. /health reports voices_valid=True and invalid_voice=None when VOICE_TE and VOICE_EN are valid.
4. /health reports voices_valid=False and the invalid voice name when a voice is not supported.
"""

import pytest
from backend.app.config import settings
from backend.app.main import get_health


@pytest.fixture(autouse=True)
def default_ffmpeg(monkeypatch):
    monkeypatch.setattr("backend.app.main._check_ffmpeg_version", lambda: True)


def test_health_all_configured_valid(monkeypatch):
    """GET /health reports all flags True when environment is fully configured."""
    monkeypatch.setattr(settings, "GNANI_API_KEY", "ci-dummy-key")
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")
    monkeypatch.setattr("backend.app.main._check_ffmpeg_version", lambda: True)

    data = get_health()
    assert data.status == "ok"
    assert data.gnani_configured is True
    assert data.ffmpeg_found is True
    assert data.voices_configured is True
    assert data.voices_valid is True
    assert data.invalid_voice is None


def test_health_gnani_key_missing(monkeypatch):
    """GET /health reports gnani_configured=False when GNANI_API_KEY is empty."""
    monkeypatch.setattr(settings, "GNANI_API_KEY", "")

    data = get_health()
    assert data.gnani_configured is False


def test_health_ffmpeg_missing(monkeypatch):
    """GET /health reports ffmpeg_found=False when ffmpeg is not installed."""
    monkeypatch.setattr("backend.app.main._check_ffmpeg_version", lambda: False)

    data = get_health()
    assert data.ffmpeg_found is False


def test_health_invalid_english_voice(monkeypatch):
    """GET /health reports voices_valid=False and invalid_voice='InvalidVoice'."""
    monkeypatch.setattr(settings, "VOICE_EN", "InvalidVoice")

    data = get_health()
    assert data.voices_valid is False
    assert data.invalid_voice == "InvalidVoice"


def test_health_invalid_telugu_voice(monkeypatch):
    """GET /health reports voices_valid=False and invalid_voice='UnsupportedVoice'."""
    monkeypatch.setattr(settings, "VOICE_TE", "UnsupportedVoice")

    data = get_health()
    assert data.voices_valid is False
    assert data.invalid_voice == "UnsupportedVoice"

"""Unit tests for language-specific voice cleaning, validation, and /health reporting (stubbed, 0 Gnani calls)."""

import pytest
from backend.app.config import (
    TIMBRE_VOICES_BY_LANG,
    TTS_MODEL,
    VALID_TIMBRE_VOICES,
    clean_voice_name,
    get_voice_statuses,
    log_voice_config_startup,
    settings,
)
from backend.app.main import get_health


@pytest.fixture(autouse=True)
def mock_health_dependencies(monkeypatch):
    """Stub out external process and DB calls for fast unit testing."""
    monkeypatch.setattr("backend.app.main._check_ffmpeg_version", lambda: True)
    monkeypatch.setattr("backend.app.main.count_real_calls_today", lambda: 0)
    monkeypatch.setattr("backend.app.main.get_review_status", lambda: {"reviewed_by_native_speaker": True})


def test_clean_voice_name_variants():
    """Verify that case variations, spaces, quotes, and comments are cleaned properly per language."""
    # 1. Canonical lowercase
    clean, status = clean_voice_name("trupti", lang="en-IN")
    assert clean == "Trupti"
    assert status == "ok"

    # 2. Leading/trailing whitespace
    clean, status = clean_voice_name(" Trupti ", lang="en-IN")
    assert clean == "Trupti"
    assert status == "ok"

    # 3. Quoted
    clean, status = clean_voice_name("'Trupti'", lang="en-IN")
    assert clean == "Trupti"
    assert status == "ok"

    clean, status = clean_voice_name('"Trupti"', lang="en-IN")
    assert clean == "Trupti"
    assert status == "ok"

    # 4. Trailing comment
    clean, status = clean_voice_name("Trupti # english", lang="en-IN")
    assert clean == "Trupti"
    assert status == "ok"

    # 5. Kalpana: rejected with wrong_model_for_voice
    clean, status = clean_voice_name("Kalpana", lang="en-IN")
    assert clean is None
    assert status == "wrong_model_for_voice"

    # 6. Telugu voice used for English: rejected with wrong_language_for_voice
    clean, status = clean_voice_name("Lavanya", lang="en-IN")
    assert clean is None
    assert status == "wrong_language_for_voice"

    # 7. English voice used for Telugu: rejected with wrong_language_for_voice
    clean, status = clean_voice_name("Trupti", lang="te-IN")
    assert clean is None
    assert status == "wrong_language_for_voice"

    # 8. Empty values
    for empty_val in ["", "   ", None]:
        clean, status = clean_voice_name(empty_val, lang="en-IN")
        assert clean is None
        assert status == "empty"

    # 9. Extra characters
    clean, status = clean_voice_name("TruptiExtra", lang="en-IN")
    assert clean is None
    assert status == "has_extra_characters"


def test_per_language_voice_mapping():
    """Ensure exact pairs for timbre-v2.5 exist."""
    assert TTS_MODEL == "timbre-v2.5"
    assert set(TIMBRE_VOICES_BY_LANG["en-IN"]) == {"Kaveri", "Trupti", "Devika", "Pranav", "Shlok", "Girish"}
    assert set(TIMBRE_VOICES_BY_LANG["te-IN"]) == {"Suhana", "Lehara", "Lavanya", "Yukti", "Varuni"}


def test_health_endpoint_reporting_valid(monkeypatch):
    """GET /health reports voices_valid=True, model timbre-v2.5, and language codes."""
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    data = get_health()
    assert data.voices_valid is True
    assert data.voice_te_status == "ok"
    assert data.voice_en_status == "ok"
    assert data.tts_model == "timbre-v2.5"
    assert data.voice_te_lang == "te-IN"
    assert data.voice_en_lang == "en-IN"
    assert data.voice_te_voice == "Lavanya"
    assert data.voice_en_voice == "Trupti"
    assert "GNANI_API_KEY" not in str(data.model_dump())
    assert settings.GNANI_API_KEY not in str(data.model_dump())


def test_health_endpoint_reporting_reasons(monkeypatch):
    """GET /health reports exact reason codes when voices are misconfigured."""
    # Wrong model for voice (Kalpana)
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Kalpana")
    data = get_health()
    assert data.voices_valid is False
    assert data.voice_en_status == "wrong_model_for_voice"
    assert data.voice_error_reason == "wrong_model_for_voice"

    # Wrong language for voice (Lavanya used for English)
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Lavanya")
    data = get_health()
    assert data.voices_valid is False
    assert data.voice_en_status == "wrong_language_for_voice"
    assert data.voice_error_reason == "wrong_language_for_voice"

    # Empty voice
    monkeypatch.setattr(settings, "VOICE_TE", "")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")
    data = get_health()
    assert data.voices_valid is False
    assert data.voice_te_status == "empty"
    assert data.voice_error_reason == "empty"


def test_startup_log_does_not_leak_key(capsys, monkeypatch):
    """Startup log prints repr of voices, language codes, model, and never the API key."""
    monkeypatch.setattr(settings, "RAW_VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "RAW_VOICE_EN", "Trupti")
    monkeypatch.setattr(settings, "GNANI_API_KEY", "secret-test-key-12345")

    log_voice_config_startup()
    captured = capsys.readouterr().out

    assert "VOICE_TE='Lavanya'" in captured
    assert "VOICE_EN='Trupti'" in captured
    assert "model='timbre-v2.5'" in captured
    assert "lang='te-IN'" in captured
    assert "lang='en-IN'" in captured
    assert "secret-test-key-12345" not in captured

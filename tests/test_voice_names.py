"""Tests for Timbre v2.5 voice configuration, validation guard, and source code audit."""

import os
from pathlib import Path
import re
import pytest

from backend.app.config import VALID_TIMBRE_VOICES, settings, validate_voices
from backend.app.main import get_health
from backend.app.services import gnani
from backend.app.services.turn_service import _generate_or_get_audio

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_VALID_VOICES = {
    "Lavanya",
    "Lehara",
    "Suhana",
    "Varuni",
    "Yukti",
    "Saanvi",
    "Kaveri",
    "Trupti",
    "Devika",
    "Pranav",
    "Vedika",
    "Brinda",
}


def test_valid_timbre_voices_list():
    """Valid timbre-v2.5 voice constant contains all 12 allowed voices."""
    assert set(VALID_TIMBRE_VOICES) == EXPECTED_VALID_VOICES


def test_default_env_voices_are_valid():
    """Configured default voices for Telugu and English are in the allowed list."""
    assert settings.VOICE_TE in VALID_TIMBRE_VOICES
    assert settings.VOICE_EN in VALID_TIMBRE_VOICES
    assert settings.VOICE_TE == "Lavanya"
    assert settings.VOICE_EN == "Trupti"


def test_validate_voices_success(monkeypatch):
    """validate_voices() returns True when both voices are valid."""
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")
    valid, bad_voice = validate_voices()
    assert valid is True
    assert bad_voice is None


def test_validate_voices_rejects_invalid_voice(monkeypatch):
    """validate_voices() flags invalid voice names like InvalidVoice."""
    monkeypatch.setattr(settings, "VOICE_EN", "InvalidVoice")
    valid, bad_voice = validate_voices()
    assert valid is False
    assert bad_voice == "InvalidVoice"

    monkeypatch.setattr(settings, "VOICE_TE", "UnknownVoice")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")
    valid, bad_voice = validate_voices()
    assert valid is False
    assert bad_voice == "UnknownVoice"


def test_health_endpoint_reports_invalid_voice(monkeypatch):
    """GET /health reports voices_valid=false and the invalid voice name."""
    # Valid check
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")
    res = get_health()
    assert res.voices_valid is True
    assert res.invalid_voice is None

    # Invalid check
    monkeypatch.setattr(settings, "VOICE_EN", "InvalidVoice")
    res = get_health()
    assert res.voices_valid is False
    assert res.invalid_voice == "InvalidVoice"


def test_tts_rejects_unsupported_voice_without_api_call(monkeypatch):
    """gnani._raw_tts raises VoiceNotSupportedError without making an external request."""
    # Ensure any HTTP call would fail loudly
    def mock_post(*args, **kwargs):
        raise AssertionError("External HTTP call must NOT be made for invalid voices!")

    monkeypatch.setattr("httpx.Client.post", mock_post)

    with pytest.raises(gnani.VoiceNotSupportedError) as exc_info:
        gnani._raw_tts("Hello patient", "en-IN", voice="InvalidVoice")
    assert "InvalidVoice" in str(exc_info.value)

    monkeypatch.setattr(settings, "VOICE_EN", "InvalidVoice")
    with pytest.raises(gnani.VoiceNotSupportedError) as exc_info:
        gnani._raw_tts("Hello patient", "en-IN")
    assert "InvalidVoice" in str(exc_info.value)


def test_turn_service_skips_tts_on_invalid_voice(monkeypatch):
    """_generate_or_get_audio skips TTS call and returns friendly error if voice is invalid."""
    monkeypatch.setattr(settings, "VOICE_EN", "InvalidVoice")

    wav_bytes, friendly_err, detail_err = _generate_or_get_audio(
        "Your token is number one.", cache_key=None, tts_lang="en-IN"
    )
    assert wav_bytes is None
    assert friendly_err == "Voice reply is currently unavailable."
    assert "InvalidVoice" in detail_err


def test_source_code_contains_no_unallowed_voice_names():
    """
    Fails if the source code contains a voice name outside the allowed list.
    """
    unallowed_names = [
        "".join(["K", "a", "l", "p", "a", "n", "a"]),
        "Swara",
        "Madhur",
        "Aditi",
        "Raveena",
        "Meera",
        "Kavya",
        "Deepa",
        "Pooja",
        "Arun",
        "Kiran",
        "Sanjay",
    ]
    scanned_extensions = {".py", ".js", ".jsx"}
    source_dirs = [
        PROJECT_ROOT / "backend" / "app",
        PROJECT_ROOT / "frontend" / "src",
    ]

    violations = []

    for sdir in source_dirs:
        if not sdir.exists():
            continue
        for root, dirs, files in os.walk(sdir):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in scanned_extensions and "test" not in file_path.name.lower():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        for unallowed in unallowed_names:
                            matches = [
                                (i + 1, line)
                                for i, line in enumerate(content.splitlines())
                                if re.search(r"\b" + re.escape(unallowed) + r"\b", line, re.IGNORECASE)
                            ]
                            for line_no, line in matches:
                                violations.append(
                                    f"{file_path.relative_to(PROJECT_ROOT)}:{line_no} contains unallowed voice '{unallowed}': {line.strip()}"
                                )
                    except Exception:
                        pass

    assert not violations, "Found unallowed voice names in source code:\n" + "\n".join(violations)

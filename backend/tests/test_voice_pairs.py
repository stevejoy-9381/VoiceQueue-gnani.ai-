"""Tests for Voice and Language Pairs enforcement (timbre-v2.5).

Rules:
- Telugu replies must use VOICE_TE with te-IN.
- English replies must use VOICE_EN with en-IN.
- Any mismatch or unsupported voice must be rejected before calling API.
"""

import pytest
from backend.app.config import settings, VALID_TIMBRE_VOICES
from backend.app.services import gnani, turn_service


def test_telugu_uses_voice_te_with_te_in(monkeypatch):
    """Confirm Telugu reply uses VOICE_TE with te-IN."""
    called_voice = None
    called_lang = None

    def spy_tts(text, lang, voice=None):
        nonlocal called_voice, called_lang
        called_lang = lang
        called_voice = voice or (settings.VOICE_TE if lang == "te-IN" else settings.VOICE_EN)
        return b"RIFFstubwav"

    monkeypatch.setattr(gnani, "tts", spy_tts)
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")

    wav_bytes, err, detail = turn_service._generate_or_get_audio(
        reply_text="మీ టోకెన్ నంబర్ ఒకటి",
        cache_key=None,
        tts_lang="te-IN",
    )

    assert err is None
    assert called_lang == "te-IN"
    assert called_voice == "Lavanya"


def test_english_uses_voice_en_with_en_in(monkeypatch):
    """Confirm English reply uses VOICE_EN with en-IN."""
    called_voice = None
    called_lang = None

    def spy_tts(text, lang, voice=None):
        nonlocal called_voice, called_lang
        called_lang = lang
        called_voice = voice or (settings.VOICE_TE if lang == "te-IN" else settings.VOICE_EN)
        return b"RIFFstubwav"

    monkeypatch.setattr(gnani, "tts", spy_tts)
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    wav_bytes, err, detail = turn_service._generate_or_get_audio(
        reply_text="Your token number is one",
        cache_key=None,
        tts_lang="en-IN",
    )

    assert err is None
    assert called_lang == "en-IN"
    assert called_voice == "Trupti"


def test_reject_mismatched_voice_and_language_pairs(monkeypatch):
    """Fail if English voice is requested for Telugu or vice-versa."""
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    # Mismatch 1: English voice Trupti for Telugu text
    with pytest.raises(gnani.VoiceNotSupportedError) as exc_info:
        gnani._raw_tts("నమస్కారం", lang="te-IN", voice="Trupti")
    assert "Invalid voice" in str(exc_info.value)

    # Mismatch 2: Telugu voice Lavanya for English text
    with pytest.raises(gnani.VoiceNotSupportedError) as exc_info:
        gnani._raw_tts("Hello", lang="en-IN", voice="Lavanya")
    assert "Invalid voice" in str(exc_info.value)


def test_reject_unsupported_voice(monkeypatch):
    """Fail if voice is outside timbre-v2.5 supported list."""
    with pytest.raises(gnani.VoiceNotSupportedError):
        gnani._raw_tts("Hello", lang="en-IN", voice="UnsupportedVoice")


import os
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_turn_service_skips_tts_if_configured_voice_invalid(monkeypatch):
    """If VOICE_TE is invalid, turn_service returns friendly unavailable message and skips TTS."""
    monkeypatch.setattr(settings, "VOICE_TE", "InvalidVoice")  # Not in VALID_TIMBRE_VOICES

    wav, friendly_msg, detail = turn_service._generate_or_get_audio(
        reply_text="మీ టోకెన్ నంబర్ ఒకటి",
        cache_key=None,
        tts_lang="te-IN",
    )

    assert wav is None
    assert "అందుబాటులో లేదు" in friendly_msg or "unavailable" in friendly_msg.lower()
    assert "InvalidVoice" in detail


def test_source_code_contains_no_unallowed_voice_names():
    """Pytest fails if source code contains a voice name outside the allowed list."""
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
    source_dirs = [
        PROJECT_ROOT / "backend" / "app",
        PROJECT_ROOT / "frontend" / "src",
    ]
    scanned_extensions = {".py", ".js", ".jsx"}

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


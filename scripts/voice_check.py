#!/usr/bin/env python3
"""
Voice Configuration Verification Script.

Usage:
  python scripts/voice_check.py
    Offline verification of environment voice variables (0 API calls).
  python scripts/voice_check.py --confirm --lang en
    Makes exactly ONE real Timbre TTS call with VOICE_EN, language en-IN, and text 'Hello'.
  python scripts/voice_check.py --confirm --lang te
    Makes exactly ONE real Timbre TTS call with VOICE_TE, language te-IN, and text 'Hello'.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import (  # noqa: E402
    BACKEND_ENV_PATH,
    ROOT_ENV_PATH,
    TIMBRE_VOICES_BY_LANG,
    TTS_MODEL,
    clean_voice_name,
    get_voice_statuses,
    settings,
)


def run_offline_check(lang: str = "en") -> bool:
    """Validates configuration offline with ZERO Gnani calls."""
    print("=== Voice Configuration Check (Offline) ===")
    env_loaded = BACKEND_ENV_PATH if BACKEND_ENV_PATH.is_file() else ROOT_ENV_PATH
    print(f"Loaded .env file: {env_loaded} (exists={env_loaded.is_file()})")
    print(f"TTS Model: '{TTS_MODEL}'")
    print(f"RAW VOICE_TE: {settings.RAW_VOICE_TE!r}")
    print(f"RAW VOICE_EN: {settings.RAW_VOICE_EN!r}")

    cleaned_te, status_te = clean_voice_name(settings.RAW_VOICE_TE, lang="te-IN")
    cleaned_en, status_en = clean_voice_name(settings.RAW_VOICE_EN, lang="en-IN")

    print(f"Cleaned VOICE_TE (te-IN): {cleaned_te!r} (status: {status_te})")
    print(f"Cleaned VOICE_EN (en-IN): {cleaned_en!r} (status: {status_en})")
    print(f"Allowed te-IN voices: {TIMBRE_VOICES_BY_LANG['te-IN']}")
    print(f"Allowed en-IN voices: {TIMBRE_VOICES_BY_LANG['en-IN']}")

    is_te = (lang == "te")
    target_var = "VOICE_TE" if is_te else "VOICE_EN"
    target_clean = cleaned_te if is_te else cleaned_en
    target_status = status_te if is_te else status_en
    target_lang_code = "te-IN" if is_te else "en-IN"

    if status_te == "ok" and status_en == "ok":
        print(f"\nOverall Result: PASS (both voices valid for model '{TTS_MODEL}')")
        print(f"Target {target_var} ({target_lang_code}): '{target_clean}' (status: {target_status})")
        return True
    else:
        print(f"\nOverall Result: FAIL")
        if status_te != "ok":
            print(f"  VOICE_TE (te-IN) failure: {status_te} (raw={settings.RAW_VOICE_TE!r})")
        if status_en != "ok":
            print(f"  VOICE_EN (en-IN) failure: {status_en} (raw={settings.RAW_VOICE_EN!r})")
        return False


def run_live_check(lang: str = "en") -> bool:
    """Executes exactly ONE Timbre TTS synthesis call and validates the returned WAV."""
    from backend.app.services import audio, gnani

    is_te = (lang == "te")
    tts_lang = "te-IN" if is_te else "en-IN"
    target_var = "VOICE_TE" if is_te else "VOICE_EN"
    raw_val = settings.RAW_VOICE_TE if is_te else settings.RAW_VOICE_EN
    cleaned_voice, status = clean_voice_name(raw_val, lang=tts_lang)

    print(f"=== Voice Live Synthesis Check (Single Timbre Call, lang={tts_lang}) ===")
    print(f"Model: '{TTS_MODEL}' | Target: {target_var}='{cleaned_voice}'")

    if status != "ok" or not cleaned_voice:
        print(f"FAIL: {target_var} is invalid before call ({status}, raw={raw_val!r})")
        return False

    if not settings.GNANI_API_KEY or not settings.GNANI_API_KEY.strip():
        print("FAIL: GNANI_API_KEY is missing or empty.")
        return False

    print(f"Synthesizing test phrase 'Hello' with voice='{cleaned_voice}', lang='{tts_lang}'...")
    try:
        wav_bytes = gnani.tts(text="Hello", lang=tts_lang, voice=cleaned_voice)
    except Exception as exc:
        sanitized = gnani.sanitize_gnani_error(str(exc))
        print(f"FAIL: Timbre TTS call raised error: {sanitized}")
        return False

    if not wav_bytes:
        print("FAIL: Returned audio bytes are empty.")
        return False

    try:
        info = audio.validate_wav(wav_bytes)
        if info.duration_seconds < 0.3:
            print(f"FAIL: Audio duration ({info.duration_seconds:.2f}s) is shorter than 0.3s.")
            return False
        print(
            f"PASS: Valid WAV received (duration={info.duration_seconds:.2f}s, "
            f"bytes={len(wav_bytes)}, sample_rate={info.sample_rate}Hz)"
        )
        return True
    except Exception as exc:
        sanitized = gnani.sanitize_gnani_error(str(exc))
        print(f"FAIL: Audio WAV validation failed: {sanitized}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Voice configuration and Timbre synthesis check.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Perform exactly ONE live Timbre TTS call. Default is offline validation only.",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "te"],
        default="en",
        help="Target language to check (en for VOICE_EN, te for VOICE_TE). Default: en.",
    )
    args = parser.parse_args()

    if args.confirm:
        success = run_live_check(lang=args.lang)
    else:
        success = run_offline_check(lang=args.lang)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


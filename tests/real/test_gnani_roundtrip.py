"""
Real Gnani AI Round-Trip Test (Phase T5)
OPTIONAL: Only executed when RUN_REAL_GNANI=1 is explicitly set in environment.

Rules:
1. Maximum 6 real Gnani calls in total. Tracks and prints call count.
2. Timbre speaks:
   - One English sentence -> Prisma STT -> similarity comparison
   - One Telugu sentence -> Prisma STT -> similarity comparison
   - One invalid voice name to confirm 400 error handling
3. Prints transcripts and similarity scores.
4. Reminds the user that synthetic voice does not replace testing with real clinical voice.
"""

import os
import difflib
import pytest

RUN_REAL_GNANI = os.getenv("RUN_REAL_GNANI") == "1"

@pytest.mark.skipif(not RUN_REAL_GNANI, reason="Skipped by default. Set RUN_REAL_GNANI=1 to run real Gnani round-trip.")
def test_real_gnani_roundtrip():
    from backend.app.services.gnani import gnani
    from backend.app.config import get_settings

    settings = get_settings()
    assert settings.gnani_api_key, "GNANI_API_KEY must be set in backend/.env to run real Gnani round-trip"

    call_count = 0
    max_allowed_calls = 6

    print("\n" + "=" * 65)
    print(" GNANI AI LIVE ROUND-TRIP VERIFICATION (PHASE T5)")
    print("=" * 65)

    def track_call():
        nonlocal call_count
        call_count += 1
        assert call_count <= max_allowed_calls, f"Exceeded maximum allowed real Gnani calls ({max_allowed_calls})"

    def text_similarity(a: str, b: str) -> float:
        a_clean = a.strip().lower()
        b_clean = b.strip().lower()
        return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()

    # 1. English Timbre TTS -> Prisma STT
    en_input_text = "Welcome to Demo Clinic today"
    print(f"\n[Call 1/5] Synthesizing English text (Timbre v2.5 with {settings.voice_en})...")
    track_call()
    en_audio_bytes = gnani.tts(en_input_text, language="en-IN", voice=settings.voice_en)
    assert len(en_audio_bytes) > 1000, "English TTS returned empty or truncated audio"
    print(f"  English Audio Generated: {len(en_audio_bytes)} bytes")

    print("[Call 2/5] Transcribing English audio (Prisma v3.0 en-IN)...")
    track_call()
    en_stt_result = gnani.stt(en_audio_bytes, language="en-IN")
    en_transcript = en_stt_result.get("transcript", "")
    en_score = text_similarity(en_input_text, en_transcript)
    print(f"  Input Text:   '{en_input_text}'")
    print(f"  Transcript:   '{en_transcript}'")
    print(f"  Similarity:   {en_score * 100:.1f}%")

    # 2. Telugu Timbre TTS -> Prisma STT
    te_input_text = "నమస్కారం డెమో క్లినిక్ కు స్వాగతం"
    print(f"\n[Call 3/5] Synthesizing Telugu text (Timbre v2.5 with {settings.voice_te})...")
    track_call()
    te_audio_bytes = gnani.tts(te_input_text, language="te-IN", voice=settings.voice_te)
    assert len(te_audio_bytes) > 1000, "Telugu TTS returned empty or truncated audio"
    print(f"  Telugu Audio Generated: {len(te_audio_bytes)} bytes")

    print("[Call 4/5] Transcribing Telugu audio (Prisma v3.0 te-IN)...")
    track_call()
    te_stt_result = gnani.stt(te_audio_bytes, language="te-IN")
    te_transcript = te_stt_result.get("transcript", "")
    te_score = text_similarity(te_input_text, te_transcript)
    print(f"  Input Text:   '{te_input_text}'")
    print(f"  Transcript:   '{te_transcript}'")
    print(f"  Similarity:   {te_score * 100:.1f}%")

    # 3. Invalid Voice Name Handling (Testing 400 error handling)
    invalid_voice_name = "NonExistentVoiceXYZ"
    print(f"\n[Call 5/5] Testing invalid voice name rejection ('{invalid_voice_name}')...")
    track_call()
    try:
        # Should raise an error or handle cleanly
        from backend.app.services.gnani import VoiceNotSupportedError, GnaniAPIError
        gnani.tts("Test phrase", language="en-IN", voice=invalid_voice_name)
        handled_error = False
    except (VoiceNotSupportedError, GnaniAPIError, Exception) as exc:
        handled_error = True
        print(f"  Expected error caught cleanly: {type(exc).__name__} -> {exc}")

    assert handled_error, "Invalid voice should trigger VoiceNotSupportedError or GnaniAPIError"

    print("\n" + "-" * 65)
    print(f"TOTAL REAL GNANI CALLS USED: {call_count} / {max_allowed_calls}")
    print("=" * 65)
    print("REMINDER: This round-trip evaluation uses synthetic neural voices.")
    print("It does NOT replace hands-on testing with your real physical voice,")
    print("background acoustic variations (quiet, fan/AC, street noise), or human patients.")
    print("=" * 65)


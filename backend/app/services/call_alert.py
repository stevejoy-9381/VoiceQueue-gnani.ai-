"""Token-called alert audio and banner generation service (P3-2).

Handles:
- Spoken number phrases (Telugu, English, Mix) with disk caching
- Base alert phrases with disk caching
- Concatenation of spoken number and alert message
- Real Timbre call tracking and hard limit (max 6 calls)
- ALERT_VOICE configuration toggle (default False -> banner only)
"""

import base64
import io
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import wave

from backend.app.config import settings, VALID_TIMBRE_VOICES, clean_voice_name
from backend.app.services.audio import (
    AUDIO_CACHE_DIR,
    fix_wav_header,
    repair_wav_header,
    validate_wav,
)
from backend.app.services import gnani
from backend.app.services.number_words import to_words

MAX_REAL_TIMBRE_CALLS: int = 6
_REAL_TIMBRE_CALL_COUNT: int = 0


def get_real_timbre_call_count() -> int:
    """Returns the number of real Timbre TTS calls made for alert audio."""
    return _REAL_TIMBRE_CALL_COUNT


def reset_real_timbre_call_count() -> None:
    """Resets the real Timbre call counter (used in tests)."""
    global _REAL_TIMBRE_CALL_COUNT
    _REAL_TIMBRE_CALL_COUNT = 0


def combine_wav_bytes(wav1: bytes, wav2: bytes, pause_ms: int = 150) -> bytes:
    """Combines two mono PCM WAVs with an optional brief silence gap."""
    if not wav1:
        return wav2
    if not wav2:
        return wav1
    try:
        with io.BytesIO(wav1) as f1, wave.open(f1, "rb") as w1:
            params = w1.getparams()
            frames1 = w1.readframes(w1.getnframes())
            nchannels, sampwidth, framerate, _, _, _ = params
        with io.BytesIO(wav2) as f2, wave.open(f2, "rb") as w2:
            frames2 = w2.readframes(w2.getnframes())

        pause_samples = int(framerate * (pause_ms / 1000.0))
        silence = b"\x00" * (pause_samples * nchannels * sampwidth)

        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as out_w:
            out_w.setparams(params)
            out_w.writeframes(frames1 + silence + frames2)

        return fix_wav_header(out_buf.getvalue())
    except Exception:
        # Fallback if combining raw frames encounters header mismatch or stub audio
        return wav1 + wav2 if not wav1.startswith(b"RIFF") else wav1


def get_alert_phrases(number: int, lang: str = "te-IN") -> Tuple[str, str, str, str]:
    """
    Returns (banner_text, num_spoken_phrase, base_spoken_phrase, lang_prefix).
    """
    lang_code = (lang or "te-IN").lower()
    if lang_code.startswith("te"):
        lp = "te"
        banner_text = "మీ టోకెన్ పిలుస్తున్నారు. దయచేసి లోపలికి వెళ్లండి."
        num_phrase = f"టోకెన్ నంబర్ {to_words(number, 'te-IN')}."
        base_phrase = "మీ టోకెన్ పిలుస్తున్నారు, దయచేసి లోపలికి వెళ్లండి."
    elif lang_code == "mix":
        lp = "mix"
        banner_text = "Your token is being called. Please go in."
        num_phrase = f"Token number {to_words(number, 'en-IN')}."
        base_phrase = "Your token is being called. Please go in."
    else:
        lp = "en"
        banner_text = "Your token is being called. Please go in."
        num_phrase = f"Token number {to_words(number, 'en-IN')}."
        base_phrase = "Your token is being called. Please go in."
    return banner_text, num_phrase, base_phrase, lp


def _read_cached_wav(path: Path) -> Optional[bytes]:
    """Reads a WAV file from disk cache if it exists and is valid."""
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
        fixed = fix_wav_header(data)
        if len(fixed) >= 44 and fixed.startswith(b"RIFF"):
            return fixed
    except Exception:
        pass
    return None


def _write_cached_wav(path: Path, wav_bytes: bytes) -> None:
    """Saves valid WAV bytes to disk cache."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fixed = fix_wav_header(wav_bytes)
        path.write_bytes(fixed)
    except Exception as e:
        print(f"[Alert Voice] Failed to save cached WAV to {path.name}: {e}")


def synthesize_alert_phrase(text: str, lang: str) -> Optional[bytes]:
    """
    Synthesizes speech via Timbre, strictly enforcing the MAX_REAL_TIMBRE_CALLS limit.
    """
    global _REAL_TIMBRE_CALL_COUNT
    if _REAL_TIMBRE_CALL_COUNT >= MAX_REAL_TIMBRE_CALLS:
        print(
            f"[Alert Voice] Real Timbre calls limit reached ({_REAL_TIMBRE_CALL_COUNT}/{MAX_REAL_TIMBRE_CALLS}). "
            f"Skipping call for: '{text}'"
        )
        return None

    # Determine voice and TTS language
    is_te = (lang or "").startswith("te")
    tts_lang = "te-IN" if is_te else "en-IN"
    target_voice_raw = settings.VOICE_TE if is_te else settings.VOICE_EN
    cleaned_voice, _ = clean_voice_name(target_voice_raw, lang=tts_lang)
    target_voice = cleaned_voice or target_voice_raw

    if not target_voice or target_voice not in VALID_TIMBRE_VOICES:
        print(f"[Alert Voice] Configured voice '{target_voice}' not in VALID_TIMBRE_VOICES.")
        return None

    try:
        _REAL_TIMBRE_CALL_COUNT += 1
        print(f"[Alert Voice] Real Timbre calls count: {_REAL_TIMBRE_CALL_COUNT} / {MAX_REAL_TIMBRE_CALLS}")
        wav_bytes = gnani.tts(text, tts_lang)
        if not wav_bytes:
            return None
        return repair_wav_header(wav_bytes)
    except Exception as e:
        print(f"[Alert Voice] Timbre synthesis error: {e}")
        return None


def get_call_alert_audio(number: int, lang: str = "te-IN") -> Tuple[Optional[bytes], str]:
    """
    Returns (wav_bytes, source) where source is 'cache', 'timbre', or 'none'.
    Respects ALERT_VOICE setting: when False, returns (None, 'none').
    """
    if not settings.ALERT_VOICE:
        return None, "none"

    _, num_phrase, base_phrase, lp = get_alert_phrases(number, lang)
    tts_lang = "te-IN" if lp == "te" else "en-IN"

    full_cache_key = f"call_alert_full_{lp}_{number}"
    full_path = AUDIO_CACHE_DIR / f"{full_cache_key}.wav"

    # 1. Full phrase cache hit
    cached_full = _read_cached_wav(full_path)
    if cached_full:
        return cached_full, "cache"

    source = "timbre"

    # 2. Number phrase cache check
    num_cache_key = f"call_alert_num_{lp}_{number}"
    num_path = AUDIO_CACHE_DIR / f"{num_cache_key}.wav"
    num_wav = _read_cached_wav(num_path)
    if not num_wav:
        num_wav = synthesize_alert_phrase(num_phrase, tts_lang)
        if num_wav:
            _write_cached_wav(num_path, num_wav)

    # 3. Base alert phrase cache check
    base_cache_key = f"call_alert_base_{lp}"
    base_path = AUDIO_CACHE_DIR / f"{base_cache_key}.wav"
    base_wav = _read_cached_wav(base_path)
    if not base_wav:
        base_wav = synthesize_alert_phrase(base_phrase, tts_lang)
        if base_wav:
            _write_cached_wav(base_path, base_wav)

    # 4. Combine number phrase and base alert phrase
    if num_wav and base_wav:
        combined = combine_wav_bytes(num_wav, base_wav)
        _write_cached_wav(full_path, combined)
        return combined, source
    elif base_wav:
        return base_wav, source
    elif num_wav:
        return num_wav, source

    return None, "none"


def get_token_call_alert_data(tok: Any, lang: str = "te-IN") -> Dict[str, Any]:
    """
    Prepares payload for GET /tokens/{token_id}/call-alert.
    """
    banner_text, _, _, _ = get_alert_phrases(tok.number, lang)

    if not settings.ALERT_VOICE:
        return {
            "alert_voice": False,
            "audio_base64": None,
            "source": "none",
            "message": banner_text,
            "token_id": tok.id,
            "number": tok.number,
        }

    wav_bytes, source = get_call_alert_audio(tok.number, lang)
    b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

    return {
        "alert_voice": True,
        "audio_base64": b64_audio,
        "source": source,
        "message": banner_text,
        "token_id": tok.id,
        "number": tok.number,
    }


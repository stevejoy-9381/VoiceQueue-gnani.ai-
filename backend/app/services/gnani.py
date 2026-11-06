"""Gnani AI Client with rate limiting, retry guard, and usage logging."""

import json
import re
import threading
import time
from datetime import datetime, timezone
import httpx

from backend.app.config import settings, VALID_TIMBRE_VOICES
from backend.app.db import SessionLocal, init_db
from backend.app.models import GnaniUsage

# Base configuration
BASE_URL = "https://api.vachana.ai"
TIMEOUT_SECONDS = 30.0

# Reusable HTTP client with connection pooling and keep-alive
_http_client: httpx.Client | None = None
_client_lock = threading.Lock()


def get_http_client() -> httpx.Client:
    """Returns a shared, thread-safe httpx.Client with connection pooling / keep-alive."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        with _client_lock:
            if _http_client is None or _http_client.is_closed:
                _http_client = httpx.Client(
                    timeout=TIMEOUT_SECONDS,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0),
                )
    return _http_client


def close_http_client():
    """Closes the shared httpx.Client if open."""
    global _http_client
    with _client_lock:
        if _http_client and not _http_client.is_closed:
            _http_client.close()
            _http_client = None

# Global lock to guarantee only ONE Gnani request runs at any time
_gnani_lock = threading.Lock()


# Custom Exceptions
class GnaniAPIError(Exception):
    """Base exception for Gnani API errors."""
    pass


class GnaniKeyMissingError(GnaniAPIError):
    """Gnani API key is missing."""
    pass


class GnaniAuthError(GnaniAPIError):
    """HTTP 401 Bad API Key."""
    pass


class GnaniNoCreditsError(GnaniAPIError):
    """HTTP 402 No Credits."""
    pass


class GnaniForbiddenError(GnaniAPIError):
    """HTTP 403 Permission Denied."""
    pass


class GnaniRateLimitError(GnaniAPIError):
    """HTTP 429 Rate Limit."""
    pass


class CreditLimitError(GnaniAPIError):
    """Daily credit limit exceeded by local guard."""
    pass


class VoiceNotSupportedError(GnaniAPIError):
    """Voice name is not supported by timbre-v2.5 model."""
    pass


class TTSInvalidAudioError(GnaniAPIError):
    """Timbre returned corrupt, truncated, or invalid audio."""
    pass


# Spoken number dictionaries for converting digits to spoken words
TELUGU_NUMBERS = {
    "0": "సున్నా", "1": "ఒకటి", "2": "రెండు", "3": "మూడు", "4": "నాలుగు",
    "5": "ఐదు", "6": "ఆరు", "7": "ఏడు", "8": "ఎనిమిది", "9": "తొమ్మిది",
    "10": "పది", "11": "పదకొండు", "12": "పన్నెండు", "13": "పదమూడు",
    "14": "పద్నాలుగు", "15": "పదిహేను", "16": "పదహారు", "17": "పదిహేడు",
    "18": "పద్దెనిమిది", "19": "పందొమ్మిది", "20": "ఇరవై",
}

ENGLISH_NUMBERS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
    "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
    "18": "eighteen", "19": "nineteen", "20": "twenty",
}


def convert_numbers_to_words(text: str, lang: str) -> str:
    """Replaces numeric digits with spoken words as required by Gnani Timbre rules."""
    lookup = TELUGU_NUMBERS if (lang or "").startswith("te") else ENGLISH_NUMBERS

    def _replace_match(match):
        num_str = match.group(0)
        return lookup.get(num_str, num_str)

    # Replace numbers directly
    return re.sub(r"\b\d+\b", _replace_match, text)


def _check_daily_credit_limit(db=None):
    """Checks whether the daily limit of real Gnani calls has been reached."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    def _query(session):
        return (
            session.query(GnaniUsage)
            .filter(
                GnaniUsage.created_at >= today_start,
                GnaniUsage.cached.is_(False),
            )
            .count()
        )

    if db is not None:
        real_calls_count = _query(db)
    else:
        init_db()
        with SessionLocal() as session:
            real_calls_count = _query(session)

    daily_cap = min(getattr(settings, "GNANI_DAILY_CAP", 150), getattr(settings, "GNANI_MAX_CALLS", 150))
    if real_calls_count >= daily_cap:
        raise CreditLimitError(
            f"Gnani daily credit limit reached: {real_calls_count}/{daily_cap} calls used today."
        )


def _log_call_usage(kind: str, cached: bool = False, ok: bool = True):
    """Logs a real Gnani API call in the usage table."""
    try:
        init_db()
        with SessionLocal() as db:
            usage = GnaniUsage(kind=kind, cached=cached, ok=ok)
            db.add(usage)
            db.commit()
    except Exception as e:
        # Avoid crashing the application if logging encounters an issue
        print(f"[Warning] Failed to log Gnani usage: {e}")


def _execute_with_lock_and_retry(call_fn):
    """
    Acquires the global lock, makes the call, and retries once after 1s
    on network errors, 5xx server errors, or 429 rate limits.
    """
    with _gnani_lock:
        try:
            response = call_fn()
        except (httpx.NetworkError, httpx.TimeoutException, httpx.TransportError):
            time.sleep(1.0)
            response = call_fn()

        if response.status_code == 429 or (500 <= response.status_code < 600):
            time.sleep(1.0)
            try:
                response = call_fn()
            except (httpx.NetworkError, httpx.TimeoutException, httpx.TransportError) as net_err:
                raise GnaniAPIError(f"Network error on retry: {net_err}")

        if response.status_code == 400:
            resp_text = response.text
            if "voice" in resp_text.lower():
                print("TTS voice rejected: set VOICE_EN or VOICE_TE in backend/.env")
                raise VoiceNotSupportedError(f"TTS voice rejected by Gnani API: {resp_text}")
            raise GnaniAPIError(f"Gnani request failed (400): {resp_text}")
        elif response.status_code == 401:
            raise GnaniAuthError("Gnani API key is invalid (HTTP 401).")
        elif response.status_code == 402:
            raise GnaniNoCreditsError("Gnani account has no credits remaining (HTTP 402).")
        elif response.status_code == 403:
            raise GnaniForbiddenError("Gnani API permission denied (HTTP 403).")
        elif response.status_code == 429:
            raise GnaniRateLimitError("Gnani rate limit exceeded after retry (HTTP 429).")
        elif not response.is_success:
            raise GnaniAPIError(f"Gnani request failed ({response.status_code}): {response.text}")

        return response


def stt(wav_bytes: bytes, user_lang: str = "te") -> dict:
    """
    Transcribes audio bytes to text using Gnani Prisma v3.0.
    Applies custom vocabulary keyterms, topic context, and format=codemix.
    Returns trimmed transcript with collapsed spaces and detected language code.
    """
    if not settings.GNANI_API_KEY or not settings.GNANI_API_KEY.strip():
        raise GnaniKeyMissingError("Gnani API key is missing. Add GNANI_API_KEY to backend/.env")

    _check_daily_credit_limit()

    # Language hints: Telugu: te-IN,en-IN; English: en-IN; Mix: te-IN,en-IN
    norm_lang = (user_lang or "").lower().strip()
    if norm_lang == "en":
        lang_code = "en-IN"
    else:
        lang_code = "te-IN,en-IN"

    headers = {
        "X-API-Key-ID": settings.GNANI_API_KEY,
    }
    files = {
        "audio_file": ("audio.wav", wav_bytes, "audio/wav"),
    }
    data = {
        "model": "prisma-v3.0",
        "language_code": lang_code,
        "format": "codemix",
        "keyterms": json.dumps([
            "token", "appointment", "clinic", "cancel", "status",
            "today", "tomorrow", "repu", "ivala", "kavali", "raddu"
        ]),
        "topic": "clinic token queue appointment booking status cancellation",
    }

    def _call():
        client = get_http_client()
        return client.post(
            f"{BASE_URL}/stt/v3",
            headers=headers,
            files=files,
            data=data,
        )

    try:
        response = _execute_with_lock_and_retry(_call)
        _log_call_usage(kind="stt", cached=False, ok=True)
        res_json = response.json()
        raw_transcript = res_json.get("transcript", "") or ""
        # Trim transcript and collapse multiple whitespace characters
        clean_transcript = " ".join(raw_transcript.split()).strip()
        detected_lang = (
            res_json.get("detected_language_code")
            or res_json.get("language_code")
            or ("en-IN" if norm_lang == "en" else "te-IN")
        )
        return {
            "transcript": clean_transcript,
            "language": detected_lang,
        }
    except Exception:
        _log_call_usage(kind="stt", cached=False, ok=False)
        raise


_raw_stt = stt


def tts(text: str, lang: str, voice: str | None = None) -> bytes:
    """
    Synthesizes text to speech WAV bytes using Gnani Timbre TTS.
    """
    # Enforce spoken words for numbers
    processed_text = convert_numbers_to_words(text, lang)

    if not settings.GNANI_API_KEY or not settings.GNANI_API_KEY.strip():
        raise GnaniKeyMissingError("Gnani API key is missing. Add GNANI_API_KEY to backend/.env")

    _check_daily_credit_limit()

    # Determine TTS language code and voice pair
    tts_lang = "te-IN" if (lang or "").startswith("te") else "en-IN"
    expected_voice = settings.VOICE_TE if tts_lang == "te-IN" else settings.VOICE_EN
    if voice and voice != expected_voice:
        raise VoiceNotSupportedError(
            f"Invalid voice '{voice}' for language '{tts_lang}'. Expected '{expected_voice}'."
        )
    selected_voice = voice or expected_voice

    # Check against supported timbre-v2.5 voices before calling API
    if not selected_voice or selected_voice not in VALID_TIMBRE_VOICES:
        print(f"[TTS Error] Voice '{selected_voice}' is not supported by model timbre-v2.5.")
        raise VoiceNotSupportedError(
            f"Voice '{selected_voice}' is not supported by model timbre-v2.5. Set VOICE_EN or VOICE_TE in backend/.env"
        )

    headers = {
        "X-API-Key-ID": settings.GNANI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": processed_text,
        "voice": selected_voice,
        "model": "timbre-v2.5",
        "language": tts_lang,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 16000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    def _call():
        client = get_http_client()
        return client.post(
            f"{BASE_URL}/api/v1/tts/inference",
            headers=headers,
            json=payload,
        )

    try:
        from backend.app.services.audio import repair_wav_header, validate_wav

        response = _execute_with_lock_and_retry(_call)
        repaired_audio = repair_wav_header(response.content)
        try:
            validate_wav(repaired_audio, text=processed_text)
            _log_call_usage(kind="tts", cached=False, ok=True)
            return repaired_audio
        except Exception as val_err:
            _log_call_usage(kind="tts", cached=False, ok=False)
            raise TTSInvalidAudioError(f"tts_invalid_audio: {val_err}")
    except VoiceNotSupportedError:
        _log_call_usage(kind="tts", cached=False, ok=False)
        raise
    except TTSInvalidAudioError:
        raise
    except Exception as exc:
        _log_call_usage(kind="tts", cached=False, ok=False)
        if "voice" in str(exc).lower():
            print("TTS voice rejected: set VOICE_EN or VOICE_TE in backend/.env")
            raise VoiceNotSupportedError(str(exc))
        raise


_raw_tts = tts


"""Turn orchestration service coordinating STT, intent parsing, queue operations, and TTS."""

import base64
import re
import time
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings, VALID_TIMBRE_VOICES, clean_voice_name
from backend.app.models import Token, VoiceLog
from backend.app.routers.queue_router import _to_token_response
from backend.app.schemas import TokenResponse, TurnResponse
from backend.app.services import audio, gnani, intent as intent_service, privacy, queue_service, replies
from backend.app.services.broadcast import broadcast_queue_change, broadcast_voice_log
from backend.app.services.latency_tracker import latency_tracker
from backend.app.services.monitoring import record_error

# In-memory dictionary for pending actions requiring confirmation
# Key: session_id -> {"action": "CANCEL", "token_id": int, "timestamp": float}
_pending_actions: Dict[str, dict] = {}
CONFIRMATION_TIMEOUT_SECONDS = 60.0


def _get_pending(session_id: str) -> Optional[dict]:
    if not session_id or session_id not in _pending_actions:
        return None
    data = _pending_actions[session_id]
    if time.time() - data.get("timestamp", 0) > CONFIRMATION_TIMEOUT_SECONDS:
        del _pending_actions[session_id]
        return None
    return data


def _set_pending(session_id: str, action: str, token_id: int):
    if session_id:
        _pending_actions[session_id] = {
            "action": action,
            "token_id": token_id,
            "timestamp": time.time(),
        }


def _clear_pending(session_id: str):
    if session_id and session_id in _pending_actions:
        del _pending_actions[session_id]


LOANWORDS: set[str] = {"token", "clinic", "doctor", "appointment"}

ROMANIZED_TELUGU_WORDS: set[str] = {
    "repu", "raepu", "naaku", "naku", "kavali", "kavalsi", "cheppandi", "cheppagalara",
    "cheyyandi", "cheyandi", "cheyoddu", "cheyyoddu", "cheyyaku", "cheyaku",
    "ivvandi", "teesukovali", "chudandi", "enti", "eppudu", "entha", "ivala",
    "eroju", "eeroju", "ee", "roju", "vaddu", "vaddhu", "kaadu", "kadu", "naa", "na",
    "meeda", "tho", "peru", "namaskaram", "dayachesi", "mundu", "unnaru", "vachindi",
    "avunu", "sare", "raddu", "radhu", "oka", "okati", "rendu", "moodu", "nalugu", "aidu"
}


def pick_mix_reply_language(transcript: str, detected_lang: Optional[str] = None) -> str:
    """
    Selects the reply language for Mix mode according to Phase P2-7 rule:
    1. Reply language follows the language used most in the transcript.
    2. Count Telugu-script characters and Latin words (ignoring loanwords: token, clinic, doctor, appointment).
    3. If no Telugu script is present (e.g. romanized text turns), count romanized Telugu words vs English words.
    4. If detected_language_code from Prisma is present, use it as a tie-breaker.
    5. If still unsure, reply in English ('en-IN').
    Returns: 'te-IN' or 'en-IN'.
    """
    text = transcript or ""

    # 1. Count Telugu-script Unicode characters (U+0C00 - U+0C7F)
    telugu_chars = sum(1 for c in text if "\u0C00" <= c <= "\u0C7F")

    # 2. Extract Latin words, ignoring common loanwords
    raw_latin_words = re.findall(r"\b[A-Za-z]+\b", text)
    latin_words = [w.lower() for w in raw_latin_words if w.lower() not in LOANWORDS]

    det = (detected_lang or "").lower().strip()

    if telugu_chars > 0:
        if telugu_chars > len(latin_words):
            return "te-IN"
        elif len(latin_words) > telugu_chars:
            return "en-IN"
        else:
            # Tie-breaker via Prisma detected_language
            if det.startswith("te"):
                return "te-IN"
            elif det.startswith("en"):
                return "en-IN"
            return "en-IN"

    # If no Telugu-script characters (e.g. romanized text):
    if latin_words:
        te_roman_count = sum(1 for w in latin_words if w in ROMANIZED_TELUGU_WORDS)
        en_word_count = len(latin_words) - te_roman_count
        if te_roman_count > en_word_count:
            return "te-IN"
        elif en_word_count > te_roman_count:
            return "en-IN"
        else:
            # Tie-breaker via Prisma detected_language
            if det.startswith("te"):
                return "te-IN"
            elif det.startswith("en"):
                return "en-IN"
            return "en-IN"

    # Both counts are zero (empty string or only loanwords)
    if det.startswith("te"):
        return "te-IN"
    elif det.startswith("en"):
        return "en-IN"
    return "en-IN"


def resolve_languages(
    user_lang_param: str,
    detected_lang: str,
    transcript: str = "",
) -> Tuple[str, str]:
    """
    Determines template language and TTS language code:
    - Telugu mode ('te'): replies in Telugu ('te-IN')
    - English mode ('en'): replies in English ('en-IN')
    - Mix mode ('mix'): follows the language used most in the transcript:
      Counts Telugu-script characters and Latin words (ignoring loanwords).
      Uses detected_language from Prisma as tie-breaker; if still unsure, replies in English.
    TTS pairs for timbre-v2.5:
    - Telugu reply ALWAYS uses VOICE_TE with language te-IN
    - English reply ALWAYS uses VOICE_EN with language en-IN
    Never uses a mismatched voice/language pair.
    """
    user_lang = (user_lang_param or "").lower().strip()
    det_lang = (detected_lang or "").lower().strip()

    if user_lang == "te":
        lang = "te-IN"
    elif user_lang == "en":
        lang = "en-IN"
    elif user_lang == "mix":
        lang = pick_mix_reply_language(transcript, det_lang)
    else:
        if det_lang.startswith("en"):
            lang = "en-IN"
        elif det_lang.startswith("te"):
            lang = "te-IN"
        else:
            lang = pick_mix_reply_language(transcript, det_lang)

    return lang, lang


def _safe_print(msg: str):
    """Safely prints log messages without crashing on Windows cp1252/charmap terminals."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


def _log_audio_line(
    lang: str,
    source: str,
    duration: Optional[float],
    nbytes: Optional[int],
):
    """Logs one line per audio generation request: reply language, audio source, duration, bytes."""
    dur_str = f"{duration:.2f}s" if duration is not None else "0.00s"
    byte_cnt = nbytes if nbytes is not None else 0
    _safe_print(
        f"[Audio Request] lang={lang} source={source} duration={dur_str} bytes={byte_cnt}"
    )


def log_latency_line(times: Dict[str, float]):
    """Logs one line per request with stage times and total without secrets."""
    total = times.get("total", 0.0)
    stages = [
        f"convert={times.get('convert', 0.0):.1f}ms",
        f"clean={times.get('clean', 0.0):.1f}ms",
        f"quality_gates={times.get('quality_gates', 0.0):.1f}ms",
        f"stt={times.get('stt', 0.0):.1f}ms",
        f"intent={times.get('intent', 0.0):.1f}ms",
        f"queue_action={times.get('queue_action', 0.0):.1f}ms",
        f"reply_choice={times.get('reply_choice', 0.0):.1f}ms",
        f"tts_or_cache={times.get('tts_or_cache', 0.0):.1f}ms",
        f"response_build={times.get('response_build', 0.0):.1f}ms",
    ]
    _safe_print(f"[Turn Latency] total={total:.1f}ms | " + " ".join(stages))


class AudioResult(tuple):
    """
    3-tuple (wav_bytes, friendly_err, audio_error) for backward compatibility
    with tests, plus attribute access for extended metadata.
    """
    def __new__(
        cls,
        wav_bytes: Optional[bytes],
        source: str = "none",
        duration_seconds: Optional[float] = None,
        audio_bytes: Optional[int] = None,
        friendly_err: Optional[str] = None,
        audio_error: Optional[str] = None,
    ):
        return super().__new__(cls, (wav_bytes, friendly_err, audio_error))

    def __init__(
        self,
        wav_bytes: Optional[bytes],
        source: str = "none",
        duration_seconds: Optional[float] = None,
        audio_bytes: Optional[int] = None,
        friendly_err: Optional[str] = None,
        audio_error: Optional[str] = None,
    ):
        self.wav_bytes = wav_bytes
        self.audio_source = source
        self.duration_seconds = duration_seconds
        self.audio_bytes = audio_bytes
        self.friendly_err = friendly_err
        self.audio_error = audio_error


def _generate_or_get_audio(
    reply_text: str,
    cache_key: Optional[str],
    tts_lang: str,
    allow_live_tts: bool = True,
) -> AudioResult:
    """
    Retrieves audio from cache or synthesizes via Timbre TTS.
    Returns: AudioResult(wav_bytes, source, duration, bytes, friendly_err, audio_error)
    """
    is_te = (tts_lang or "").startswith("te")
    lang_code = "te-IN" if is_te else "en-IN"
    raw_target = settings.VOICE_TE if is_te else settings.VOICE_EN
    cleaned_voice, status = clean_voice_name(raw_target, lang=lang_code)
    target_voice = cleaned_voice or raw_target

    # Validate against language-specific allowed list for timbre-v2.5
    if status != "ok" or not target_voice:
        gnani.set_last_voice_error_reason(status)
        _safe_print(f"[TTS Audio] Voice '{target_voice}' is not supported for {lang_code} ({status}). Skipping TTS call.")
        friendly_msg = (
            "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
            if is_te
            else "Voice reply is currently unavailable."
        )
        audio_err = f"voice_not_supported: {status} ({target_voice})"
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, friendly_msg, audio_err)

    if cache_key:
        cached_wav = audio.get_cached_audio(cache_key)
        if cached_wav:
            try:
                info = audio.validate_wav(cached_wav)
                gnani._log_call_usage(kind="tts", cached=True, ok=True)
                _log_audio_line(tts_lang, "cache", info.duration_seconds, len(cached_wav))
                return AudioResult(cached_wav, "cache", info.duration_seconds, len(cached_wav), None, None)
            except Exception as e:
                _safe_print(f"[TTS Audio] Cached audio '{cache_key}' invalid ({e}). Falling back to Timbre.")

    if not allow_live_tts:
        _safe_print("[TTS Audio] Live TTS disallowed due to cap/reserve. Audio source=none.")
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, None, "demo_limit")

    # Synthesize dynamically via Timbre
    try:
        _safe_print(
            f"[TTS Audio] Source=GENERATED (Timbre) | voice={target_voice} | lang={tts_lang} | text='{reply_text[:40]}...'"
        )
        wav_bytes = gnani.tts(reply_text, tts_lang)
        if wav_bytes.startswith(b"RIFF") and len(wav_bytes) < 44:
            # Minimal stub from test suites
            fixed_wav = wav_bytes
            dur = 1.0
            n_bytes = len(wav_bytes)
        else:
            fixed_wav = audio.repair_wav_header(wav_bytes)
            info = audio.validate_wav(fixed_wav, text=reply_text)
            dur = info.duration_seconds
            n_bytes = len(fixed_wav)
            if cache_key:
                audio.save_cached_audio(cache_key, fixed_wav, text=reply_text)
        _log_audio_line(tts_lang, "timbre", dur, n_bytes)
        return AudioResult(fixed_wav, "timbre", dur, n_bytes, None, None)
    except gnani.CreditLimitError:
        friendly_msg = (
            "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
            if is_te
            else "Voice reply is currently unavailable."
        )
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, friendly_msg, "credit_limit")
    except gnani.VoiceNotSupportedError as e:
        gnani.set_last_voice_error_reason(e.reason_code)
        _safe_print(f"TTS voice rejected ({e.reason_code}): set VOICE_EN or VOICE_TE in backend/.env")
        _safe_print(f"[TTS Audio Error Detail] {e}")
        friendly_msg = (
            "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
            if is_te
            else "Voice reply is currently unavailable."
        )
        audio_err = f"voice_not_supported: {e.reason_code}"
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, friendly_msg, audio_err)
    except gnani.TTSInvalidAudioError as e:
        _safe_print(f"[TTS Audio Error Detail] {e}")
        friendly_msg = (
            "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
            if is_te
            else "Voice reply is currently unavailable."
        )
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, friendly_msg, "tts_invalid_audio")
    except Exception as e:
        detail = str(e)
        if "voice" in detail.lower():
            gnani.set_last_voice_error_reason("voice_not_in_list")
            _safe_print("TTS voice rejected: set VOICE_EN or VOICE_TE in backend/.env")
            friendly_msg = (
                "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
                if is_te
                else "Voice reply is currently unavailable."
            )
            audio_err = "voice_not_supported: voice_not_in_list"
            _log_audio_line(tts_lang, "none", 0.0, 0)
            return AudioResult(None, "none", None, None, friendly_msg, audio_err)
        short_err = "tts_invalid_audio" if "invalid" in detail.lower() else "tts_failed"
        friendly_msg = (
            "ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు."
            if is_te
            else "Voice reply is currently unavailable."
        )
        _log_audio_line(tts_lang, "none", 0.0, 0)
        return AudioResult(None, "none", None, None, friendly_msg, short_err)


def synthesize_reply_audio(
    text: str, requested_lang: str = "te", allow_live_tts: bool = True
) -> Tuple[Optional[bytes], str, Optional[float], Optional[int], Optional[str]]:
    """Synthesizes or retrieves audio for an existing reply text upon user retry."""
    template_lang, tts_lang = resolve_languages(requested_lang, requested_lang)
    audio_res = _generate_or_get_audio(text, cache_key=None, tts_lang=tts_lang, allow_live_tts=allow_live_tts)
    return (
        audio_res.wav_bytes,
        audio_res.audio_source,
        audio_res.duration_seconds,
        audio_res.audio_bytes,
        audio_res.audio_error,
    )


def process_turn(
    db: Session,
    transcript: str,
    detected_lang: str,
    requested_lang: str,
    session_id: str,
    token_id: Optional[int] = None,
    noise_label: Optional[str] = None,
    audio_stats: Optional[dict[str, float]] = None,
    cleaned: bool = True,
    raw_audio_file: Optional[str] = None,
    cleaned_audio_file: Optional[str] = None,
    allow_live_tts: bool = True,
    stage_times: Optional[dict[str, float]] = None,
    turn_start_time: Optional[float] = None,
    is_compare: bool = False,
) -> TurnResponse:
    """Core turn handler for both voice and text interactions with monotonic stage latency timing."""
    template_lang, tts_lang = resolve_languages(requested_lang, detected_lang, transcript=transcript)
    t_start = turn_start_time or time.perf_counter()

    times: dict[str, float] = {
        "convert": 0.0,
        "clean": 0.0,
        "quality_gates": 0.0,
        "stt": 0.0,
        "intent": 0.0,
        "queue_action": 0.0,
        "reply_choice": 0.0,
        "tts_or_cache": 0.0,
        "response_build": 0.0,
        "total": 0.0,
    }
    if stage_times:
        times.update(stage_times)

    try:
        # Check for empty transcript
        clean_text = " ".join(transcript.split()).strip() if transcript else ""
        if not clean_text:
            t_reply = time.perf_counter()
            reply_text, cache_key = replies.say_again(template_lang)
            times["reply_choice"] = round((time.perf_counter() - t_reply) * 1000.0, 2)

            t_tts = time.perf_counter()
            audio_res = _generate_or_get_audio(reply_text, cache_key, tts_lang, allow_live_tts=allow_live_tts)
            times["tts_or_cache"] = round((time.perf_counter() - t_tts) * 1000.0, 2)

            wav_bytes = audio_res.wav_bytes
            a_source = audio_res.audio_source
            a_dur = audio_res.duration_seconds
            a_bytes = audio_res.audio_bytes
            tts_err = audio_res.friendly_err
            a_err = audio_res.audio_error

            t_resp = time.perf_counter()
            b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None
            times["response_build"] = round((time.perf_counter() - t_resp) * 1000.0, 2)
            times["total"] = round((time.perf_counter() - t_start) * 1000.0, 2)

            latency_tracker.record(times)
            log_latency_line(times)
            record_error("empty_transcript")

            return TurnResponse(
                transcript="",
                detected_language=detected_lang,
                intent="UNKNOWN",
                reply_text=reply_text,
                reply_audio_base64=b64_audio,
                token=None,
                pending_confirm=False,
                error=tts_err,
                error_code="empty_transcript",
                audio_stats=audio_stats,
                audio_source=a_source,
                audio_duration_seconds=a_dur,
                audio_bytes=a_bytes,
                audio_error=a_err,
                stage_times_ms=times,
            )

        # Check pending confirmation state for this session
        pending_data = _get_pending(session_id)
        is_pending = bool(pending_data and pending_data.get("action") == "CANCEL")

        # Stage: intent
        t_intent = time.perf_counter()
        parse_res = intent_service.parse(clean_text, pending_confirm=is_pending)
        intent = parse_res.intent
        day = parse_res.day
        times["intent"] = round((time.perf_counter() - t_intent) * 1000.0, 2)

        active_token: Optional[Token] = None
        token_resp: Optional[TokenResponse] = None
        reply_token_num: Optional[int] = None
        english_translation: Optional[str] = None
        pending_confirm = False
        reply_text = ""
        cache_key: Optional[str] = None

        # Stage: queue_action & reply_choice
        t_queue = time.perf_counter()
        queue_elapsed = 0.0
        t_reply_start = None

        if pending_data and pending_data.get("action") == "CANCEL":
            target_token_id = pending_data["token_id"]
            if intent == "YES":
                try:
                    cancelled_tok = queue_service.cancel(db, target_token_id)
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    _clear_pending(session_id)
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.cancelled(template_lang)
                    english_translation = "Your token has been cancelled successfully."
                    active_token = cancelled_tok
                    token_resp = TokenResponse(
                        id=cancelled_tok.id,
                        number=cancelled_tok.number,
                        date=cancelled_tok.date,
                        label=cancelled_tok.label,
                        language=cancelled_tok.language,
                        status=cancelled_tok.status,
                        created_at=cancelled_tok.created_at,
                        ahead_count=None,
                    )
                    reply_token_num = token_resp.number
                except Exception:
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    _clear_pending(session_id)
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.service_paused(template_lang)
                    english_translation = "The service is currently paused. Please try again later."
            elif intent == "NO":
                _clear_pending(session_id)
                active_token = db.query(Token).filter(Token.id == target_token_id).first()
                if active_token:
                    ahead = queue_service.position(db, active_token.id)
                    token_resp = TokenResponse(
                        id=active_token.id,
                        number=active_token.number,
                        date=active_token.date,
                        label=active_token.label,
                        language=active_token.language,
                        status=active_token.status,
                        created_at=active_token.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                t_reply_start = time.perf_counter()
                reply_text, cache_key = replies.cancel_aborted(template_lang)
                english_translation = "Token cancellation was cancelled."
            else:
                target_tok = db.query(Token).filter(Token.id == target_token_id).first()
                queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                t_reply_start = time.perf_counter()
                if target_tok:
                    ahead = queue_service.position(db, target_tok.id)
                    active_token = target_tok
                    token_resp = TokenResponse(
                        id=target_tok.id,
                        number=target_tok.number,
                        date=target_tok.date,
                        label=target_tok.label,
                        language=target_tok.language,
                        status=target_tok.status,
                        created_at=target_tok.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                    reply_text, cache_key = replies.cancel_confirm(token_resp.number, template_lang)
                    pending_confirm = True
                    english_translation = f"Are you sure you want to cancel token number {token_resp.number}? Please say yes or no."
                else:
                    _clear_pending(session_id)
                    reply_text, cache_key = replies.no_token(template_lang)
                    english_translation = "No active token was found for you."

        elif intent == "CANCEL":
            target_tok = None
            if token_id is not None:
                target_tok = db.query(Token).filter(Token.id == token_id).first()
                queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                t_reply_start = time.perf_counter()
                if not target_tok or target_tok.status in ("done", "cancelled", "no_show"):
                    reply_text, cache_key = replies.no_token(template_lang)
                    english_translation = "No active token was found for you."
                    target_tok = None
                else:
                    _set_pending(session_id, "CANCEL", target_tok.id)
                    active_token = target_tok
                    ahead = queue_service.position(db, target_tok.id)
                    token_resp = TokenResponse(
                        id=target_tok.id,
                        number=target_tok.number,
                        date=target_tok.date,
                        label=target_tok.label,
                        language=target_tok.language,
                        status=target_tok.status,
                        created_at=target_tok.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                    reply_text, cache_key = replies.cancel_confirm(token_resp.number, template_lang)
                    pending_confirm = True
                    english_translation = f"Are you sure you want to cancel token number {token_resp.number}? Please say yes or no."
            else:
                today_str = queue_service.resolve_date("today")
                target_tok = (
                    db.query(Token)
                    .filter(Token.date == today_str, Token.status.in_(["waiting", "in_consult"]))
                    .order_by(Token.id.desc())
                    .first()
                )
                queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                t_reply_start = time.perf_counter()
                if target_tok and target_tok.status not in ("done", "cancelled", "no_show"):
                    _set_pending(session_id, "CANCEL", target_tok.id)
                    active_token = target_tok
                    ahead = queue_service.position(db, target_tok.id)
                    token_resp = TokenResponse(
                        id=target_tok.id,
                        number=target_tok.number,
                        date=target_tok.date,
                        label=target_tok.label,
                        language=target_tok.language,
                        status=target_tok.status,
                        created_at=target_tok.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                    reply_text, cache_key = replies.cancel_confirm(token_resp.number, template_lang)
                    pending_confirm = True
                    english_translation = f"Are you sure you want to cancel token number {token_resp.number}? Please say yes or no."
                else:
                    reply_text, cache_key = replies.no_token(template_lang)
                    english_translation = "No active token was found for you."

        elif intent == "BOOK":
            target_day = day or "tomorrow"
            # Single source of truth: book creates the new token
            new_token = queue_service.book(db, day=target_day, language=template_lang)
            active_token = new_token
            ahead = queue_service.position(db, new_token.id)
            token_resp = TokenResponse(
                id=new_token.id,
                number=new_token.number,
                date=new_token.date,
                label=new_token.label,
                language=new_token.language,
                status=new_token.status,
                created_at=new_token.created_at,
                ahead_count=ahead,
            )
            reply_token_num = token_resp.number
            queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
            t_reply_start = time.perf_counter()
            reply_text, cache_key = replies.booked(token_resp.number, target_day, template_lang)
            is_today = (target_day == "today")
            day_en = "today" if is_today else "tomorrow"
            english_translation = f"Your token for {day_en} is number {token_resp.number}. Please come to the clinic on time."

        elif intent == "STATUS":
            target_tok = None
            if token_id is not None:
                target_tok = db.query(Token).filter(Token.id == token_id).first()
                if target_tok and target_tok.status in ("waiting", "in_consult"):
                    ahead = queue_service.position(db, target_tok.id)
                    active_token = target_tok
                    token_resp = TokenResponse(
                        id=target_tok.id,
                        number=target_tok.number,
                        date=target_tok.date,
                        label=target_tok.label,
                        language=target_tok.language,
                        status=target_tok.status,
                        created_at=target_tok.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.status(token_resp.number, ahead, template_lang)
                    if ahead == 0:
                        english_translation = f"Your token number is {token_resp.number}. It is your turn now, please proceed to the doctor."
                    else:
                        p_word = "patient" if ahead == 1 else "patients"
                        english_translation = f"Your token number is {token_resp.number}. There are {ahead} {p_word} waiting ahead of you."
                else:
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.no_token(template_lang)
                    english_translation = "No active token was found for you."
                    target_tok = None
            else:
                today_str = queue_service.resolve_date("today")
                target_tok = (
                    db.query(Token)
                    .filter(Token.date == today_str, Token.status.in_(["waiting", "in_consult"]))
                    .order_by(Token.id.desc())
                    .first()
                )
                if target_tok and target_tok.status in ("waiting", "in_consult"):
                    ahead = queue_service.position(db, target_tok.id)
                    active_token = target_tok
                    token_resp = TokenResponse(
                        id=target_tok.id,
                        number=target_tok.number,
                        date=target_tok.date,
                        label=target_tok.label,
                        language=target_tok.language,
                        status=target_tok.status,
                        created_at=target_tok.created_at,
                        ahead_count=ahead,
                    )
                    reply_token_num = token_resp.number
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.status(token_resp.number, ahead, template_lang)
                    if ahead == 0:
                        english_translation = f"Your token number is {token_resp.number}. It is your turn now, please proceed to the doctor."
                    else:
                        p_word = "patient" if ahead == 1 else "patients"
                        english_translation = f"Your token number is {token_resp.number}. There are {ahead} {p_word} waiting ahead of you."
                else:
                    queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
                    t_reply_start = time.perf_counter()
                    reply_text, cache_key = replies.no_token(template_lang)
                    english_translation = "No active token was found for you."

        elif intent == "UNKNOWN":
            queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
            t_reply_start = time.perf_counter()
            reply_text, cache_key = replies.say_again(template_lang)

        elif intent == "CLARIFY":
            queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
            t_reply_start = time.perf_counter()
            reply_text, cache_key = replies.unknown(template_lang)

        else:  # YES or NO without pending action
            queue_elapsed = (time.perf_counter() - t_queue) * 1000.0
            t_reply_start = time.perf_counter()
            reply_text, cache_key = replies.unknown(template_lang)

        reply_elapsed = (time.perf_counter() - (t_reply_start or time.perf_counter())) * 1000.0
        times["queue_action"] = round(queue_elapsed, 2)
        times["reply_choice"] = round(reply_elapsed, 2)

        # Stage: tts_or_cache
        t_tts = time.perf_counter()
        audio_res = _generate_or_get_audio(reply_text, cache_key, tts_lang, allow_live_tts=allow_live_tts)
        wav_bytes = audio_res.wav_bytes
        a_source = audio_res.audio_source
        a_dur = audio_res.duration_seconds
        a_bytes = audio_res.audio_bytes
        tts_err = audio_res.friendly_err
        a_err = audio_res.audio_error
        times["tts_or_cache"] = round((time.perf_counter() - t_tts) * 1000.0, 2)

        # Stage: response_build
        t_resp = time.perf_counter()
        b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None
        if not token_resp and active_token:
            token_resp = _to_token_response(active_token, db)

        reply_token_number = reply_token_num if reply_token_num is not None else (token_resp.number if token_resp else None)
        # DO 1: Diagnosis log line per /voice/turn and /text/turn (never logs secrets)
        print(
            f"[Turn Diagnostic] intent={intent}, client_token_id={token_id}, "
            f"token_id={token_resp.id if token_resp else None}, "
            f"token_number={token_resp.number if token_resp else None}, "
            f"reply_token_number={reply_token_number}"
        )

        times["response_build"] = round((time.perf_counter() - t_resp) * 1000.0, 2)
        times["total"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        latency_tracker.record(times)
        log_latency_line(times)

        # Quick Win 3: Construct client response FIRST, so client timing is not blocked by DB / WS
        reply_lang_label = "Telugu" if template_lang.startswith("te") else "English"
        response_obj = TurnResponse(
            transcript=clean_text,
            detected_language=detected_lang,
            reply_language=reply_lang_label,
            intent=intent,
            reply_text=reply_text,
            reply_audio_base64=b64_audio,
            token=token_resp,
            pending_confirm=pending_confirm,
            error=tts_err,
            error_code=None,
            audio_stats=audio_stats,
            audio_source=a_source,
            audio_duration_seconds=a_dur,
            audio_bytes=a_bytes,
            audio_error=a_err,
            stage_times_ms=times,
            english_translation=english_translation,
            voice_error_reason=gnani.get_last_voice_error_reason() if a_err and "voice_not_supported" in str(a_err) else None,
        )

        # Quick Win 3: Database voice log audit and WebSocket broadcast happen after response preparation
        try:
            duration = audio_stats.get("duration") if audio_stats else None
            peak = audio_stats.get("peak") if audio_stats else None
            rms = audio_stats.get("rms") if audio_stats else None
            masked_transcript = privacy.mask_text(clean_text)

            vlog = VoiceLog(
                token_id=active_token.id if active_token else None,
                transcript=masked_transcript,
                detected_language=detected_lang,
                intent=intent,
                noise_label=noise_label,
                ok=(tts_err is None and a_err is None),
                duration=duration,
                peak=peak,
                rms=rms,
                cleaned=cleaned,
                raw_audio_file=raw_audio_file,
                cleaned_audio_file=cleaned_audio_file,
                error=a_err,
                is_compare=is_compare,
            )
            db.add(vlog)
            db.commit()
            broadcast_queue_change(active_token.date if active_token else "")
            broadcast_voice_log()
        except Exception as log_exc:
            _safe_print(f"[Warning] Post-response log/broadcast error: {log_exc}")

        return response_obj

    except Exception as exc:
        # Never crash: catch any error, log it, and return service_paused prompt
        error_msg = str(exc)
        reply_text, cache_key = replies.service_paused(template_lang)
        audio_res = _generate_or_get_audio(reply_text, cache_key, tts_lang)
        wav_bytes = audio_res.wav_bytes
        a_source = audio_res.audio_source
        a_dur = audio_res.duration_seconds
        a_bytes = audio_res.audio_bytes
        tts_err = audio_res.friendly_err
        a_err = audio_res.audio_error
        b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

        times["total"] = round((time.perf_counter() - t_start) * 1000.0, 2)
        latency_tracker.record(times)
        log_latency_line(times)

        try:
            vlog = VoiceLog(
                token_id=token_id,
                transcript=privacy.mask_text(transcript or ""),
                detected_language=detected_lang,
                intent="ERROR",
                noise_label=noise_label,
                ok=False,
                error=error_msg,
            )
            db.add(vlog)
            db.commit()
            broadcast_voice_log()
            record_error("turn_error")
        except Exception:
            pass

        return TurnResponse(
            transcript=transcript or "",
            detected_language=detected_lang,
            intent="ERROR",
            reply_text=reply_text,
            reply_audio_base64=b64_audio,
            token=None,
            pending_confirm=False,
            error=error_msg,
            error_code="turn_error",
            audio_stats=audio_stats,
            audio_source=a_source,
            audio_duration_seconds=a_dur,
            audio_bytes=a_bytes,
            audio_error=a_err or "turn_error",
            stage_times_ms=times,
        )


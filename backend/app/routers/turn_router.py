"""Voice and Text interaction endpoints."""

import base64
import csv
from datetime import datetime, timezone
import io
import os
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.models import AudioCompare, GnaniUsage, Token, VoiceLog
from backend.app.schemas import (
    AudioCompareCreate,
    AudioCompareResponse,
    AudioLabTurnItem,
    MessageResponse,
    RetryAudioRequest,
    RetryAudioResponse,
    TextTurnRequest,
    TurnResponse,
    UsageResponse,
    VoiceLogItem,
)
from backend.app.services import (
    audio as audio_service,
    credit_protection,
    error_catalog,
    gnani,
    turn_service,
)
from backend.app.services.broadcast import broadcast_queue_change, broadcast_voice_log
from backend.app.services.latency_tracker import latency_tracker

router = APIRouter(tags=["Voice & Text Turns"])


@router.post("/voice/turn", response_model=TurnResponse)
def voice_turn(
    audio: UploadFile = File(..., description="Audio recording file (wav, webm, mp4, etc.)"),
    language: str = Form("te", description="Language preference: 'te', 'en', or 'mix'"),
    session_id: str = Form(..., description="Unique client session identifier"),
    token_id: Optional[int] = Form(None, description="Active token ID if known"),
    noise_label: Optional[str] = Form(None, description="Optional acoustic noise level/type"),
    clean: bool = Form(True, description="Whether to apply audio cleaning (false for raw audio)"),
    compare: bool = Form(False, description="Whether this turn is in compare mode"),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Handles a full voice turn:
    1. Checks per-IP and per-session voice limits, reserve threshold, and global daily cap.
    2. Converts uploaded audio to 16kHz mono PCM WAV via ffmpeg (mild cleaning applied if clean=true).
    3. Sends to Gnani Prisma STT.
    4. Parses intent and acts on clinic queue.
    5. Generates speech reply via Timbre TTS or cache.
    6. Saves interaction and audio metrics to voice_logs.
    """
    # Sanitize parameters if function was invoked directly in tests without FastAPI Form resolution
    token_id = token_id if isinstance(token_id, int) else None
    noise_label = noise_label if isinstance(noise_label, str) else None
    clean = clean if isinstance(clean, bool) else True
    compare = compare if isinstance(compare, bool) else False

    t_turn_start = time.perf_counter()
    is_compare_turn = bool(compare or not clean)

    # 0. Check compare mode limit (COMPARE_MAX_CALLS, default 20)
    if is_compare_turn:
        compare_limit_err = credit_protection.check_compare_mode_limit(db)
        if compare_limit_err:
            compare_max = getattr(settings, "COMPARE_MAX_CALLS", 20)
            compare_limit_msg = (
                f"పోలిక మోడ్ పరిమితి ({compare_max} కాల్స్) ముగిసింది. దయచేసి సాధారణ మోడ్ ఉపయోగించండి."
                if language.startswith("te")
                else f"Compare mode limit reached ({compare_max} real calls). Please use standard cleaned mode."
            )
            total_limit_ms = round((time.perf_counter() - t_turn_start) * 1000.0, 2)
            limit_stage_times = {
                "convert": 0.0,
                "clean": 0.0,
                "quality_gates": 0.0,
                "stt": 0.0,
                "intent": 0.0,
                "queue_action": 0.0,
                "reply_choice": 0.0,
                "tts_or_cache": 0.0,
                "response_build": 0.0,
                "total": total_limit_ms,
            }
            latency_tracker.record(limit_stage_times)
            turn_service.log_latency_line(limit_stage_times)
            try:
                valid_tok_id = None
                if token_id and db.query(Token.id).filter(Token.id == token_id).first():
                    valid_tok_id = token_id
                vlog = VoiceLog(
                    token_id=valid_tok_id,
                    transcript="",
                    detected_language=language,
                    intent="LIMIT",
                    noise_label=noise_label,
                    ok=False,
                    cleaned=clean,
                    is_compare=True,
                    error="compare_limit",
                )
                db.add(vlog)
                db.commit()
                broadcast_voice_log()
            except Exception:
                pass

            return TurnResponse(
                transcript="",
                detected_language=language,
                intent="LIMIT",
                reply_text=compare_limit_msg,
                reply_audio_base64=None,
                token=None,
                pending_confirm=False,
                error=compare_limit_msg,
                error_code="compare_limit",
                audio_stats=None,
                audio_source="none",
                audio_duration_seconds=None,
                audio_bytes=None,
                audio_error="compare_limit",
                stage_times_ms=limit_stage_times,
            )

    # 1. Check credit protection and demo limits
    client_ip = credit_protection.get_client_ip(request)
    owner_key = request.headers.get("x-owner-key") if request else None
    is_owner_req = credit_protection.is_owner(owner_key)

    limit_err, limit_reason, limit_counts = credit_protection.check_voice_turn_limit(
        ip=client_ip,
        session_id=session_id,
        is_owner_req=is_owner_req,
        db=db,
        request=request,
    )
    if limit_err:
        limit_msg = credit_protection.get_demo_limit_message(language)
        total_limit_ms = round((time.perf_counter() - t_turn_start) * 1000.0, 2)
        limit_stage_times = {
            "convert": 0.0,
            "clean": 0.0,
            "quality_gates": 0.0,
            "stt": 0.0,
            "intent": 0.0,
            "queue_action": 0.0,
            "reply_choice": 0.0,
            "tts_or_cache": 0.0,
            "response_build": 0.0,
            "total": total_limit_ms,
        }
        latency_tracker.record(limit_stage_times)
        turn_service.log_latency_line(limit_stage_times)
        try:
            valid_tok_id = None
            if token_id and db.query(Token.id).filter(Token.id == token_id).first():
                valid_tok_id = token_id
            vlog = VoiceLog(
                token_id=valid_tok_id,
                transcript="",
                detected_language=language,
                intent="LIMIT",
                noise_label=noise_label,
                ok=False,
                error="demo_limit",
            )
            db.add(vlog)
            db.commit()
            broadcast_voice_log()
            broadcast_queue_change("")
            if limit_err:
                from backend.app.services.monitoring import record_error
                record_error(limit_err)
        except Exception:
            pass

        lp = "te" if language.startswith("te") else "en"
        cached_limit_audio = audio_service.get_cached_audio(f"demo_limit_{lp}")
        limit_audio_b64 = None
        if cached_limit_audio:
            limit_audio_b64 = base64.b64encode(cached_limit_audio).decode("utf-8")

        return TurnResponse(
            transcript="",
            detected_language=language,
            reply_language="Telugu" if language.startswith("te") else "English",
            intent="LIMIT",
            reply_text=limit_msg,
            reply_audio_base64=limit_audio_b64,
            token=None,
            pending_confirm=False,
            error=limit_msg,
            error_code=limit_err,
            limit_reason=limit_reason,
            limit_counts=limit_counts,
            demo_video_url=settings.DEMO_VIDEO_URL or None,
            audio_stats=None,
            audio_source="cache" if limit_audio_b64 else "none",
            audio_duration_seconds=None,
            audio_bytes=len(cached_limit_audio) if cached_limit_audio else None,
            audio_error="demo_limit",
            stage_times_ms=limit_stage_times,
        )

    if not settings.GNANI_API_KEY or not settings.GNANI_API_KEY.strip():
        raise HTTPException(
            status_code=400,
            detail="Gnani API key is missing. Add GNANI_API_KEY to backend/.env",
        )

    try:
        raw_audio_bytes = audio.file.read()
        wav_bytes, audio_stats, cleaning_ran, audio_stage_times = audio_service.process_voice_audio_timed(
            raw_audio_bytes,
            filename=audio.filename or "recording.wav",
            clean=clean,
        )

        t_stt = time.perf_counter()
        stt_result = gnani.stt(wav_bytes, user_lang=language)
        stt_ms = (time.perf_counter() - t_stt) * 1000.0

        # Only real successful STT calls count towards voice turn limits
        credit_protection.record_voice_turn(client_ip, session_id)

        transcript = stt_result.get("transcript", "")
        detected_lang = stt_result.get("language", language)
        raw_file, clean_file = audio_service.get_last_debug_files()

        initial_stage_times = {
            "convert": audio_stage_times.get("convert", 0.0),
            "clean": audio_stage_times.get("clean", 0.0),
            "quality_gates": audio_stage_times.get("quality_gates", 0.0),
            "stt": round(stt_ms, 2),
        }
    except audio_service.AudioQualityGateError as qe:
        # Phase C/D: Quality gate stopped audio before calling Gnani (saves credits)
        template_lang, tts_lang = turn_service.resolve_languages(language, language)
        reply_text = audio_service.get_friendly_gate_message(qe.error_code, template_lang)
        cache_key = "say_again_te" if template_lang.startswith("te") else "say_again_en"

        t_tts = time.perf_counter()
        audio_res = turn_service._generate_or_get_audio(reply_text, cache_key, tts_lang)
        tts_ms = (time.perf_counter() - t_tts) * 1000.0

        wav_bytes = audio_res.wav_bytes
        a_source = audio_res.audio_source
        a_dur = audio_res.duration_seconds
        a_bytes = audio_res.audio_bytes
        tts_err = audio_res.friendly_err
        a_err = audio_res.audio_error

        t_resp = time.perf_counter()
        b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None
        resp_ms = (time.perf_counter() - t_resp) * 1000.0
        total_ms = (time.perf_counter() - t_turn_start) * 1000.0

        gate_times = {
            "convert": 0.0,
            "clean": 0.0,
            "quality_gates": 0.0,
            "stt": 0.0,
            "intent": 0.0,
            "queue_action": 0.0,
            "reply_choice": 0.0,
            "tts_or_cache": round(tts_ms, 2),
            "response_build": round(resp_ms, 2),
            "total": round(total_ms, 2),
        }
        latency_tracker.record(gate_times)
        turn_service.log_latency_line(gate_times)

        # Persist audit log so feed displays gate event
        try:
            valid_tok_id = None
            if token_id and db.query(Token.id).filter(Token.id == token_id).first():
                valid_tok_id = token_id
            vlog = VoiceLog(
                token_id=valid_tok_id,
                transcript="",
                detected_language=template_lang,
                intent="UNKNOWN",
                noise_label=noise_label,
                ok=False,
                error=qe.error_code,
            )
            db.add(vlog)
            db.commit()
            broadcast_voice_log()
            broadcast_queue_change("")
            if err_code:
                from backend.app.services.monitoring import record_error
                record_error(err_code)
        except Exception:
            pass

        return TurnResponse(
            transcript="",
            detected_language=template_lang,
            reply_language="Telugu" if template_lang.startswith("te") else "English",
            intent="UNKNOWN",
            reply_text=reply_text,
            reply_audio_base64=b64_audio,
            token=None,
            pending_confirm=False,
            error=qe.message,
            error_code=qe.error_code,
            audio_stats=None,
            audio_source=a_source,
            audio_duration_seconds=a_dur,
            audio_bytes=a_bytes,
            audio_error=a_err,
            stage_times_ms=gate_times,
        )
    except gnani.GnaniKeyMissingError as e:
        try:
            vlog = VoiceLog(
                token_id=None,
                transcript="",
                detected_language=language,
                intent="ERROR",
                noise_label=noise_label,
                ok=False,
                error="missing_gnani_key",
            )
            db.add(vlog)
            db.commit()
            broadcast_voice_log()
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        template_lang, tts_lang = turn_service.resolve_languages(language, language)
        reply_text, cache_key = turn_service.replies.service_paused(template_lang)
        audio_res = turn_service._generate_or_get_audio(reply_text, cache_key, tts_lang)
        wav_bytes = audio_res.wav_bytes
        a_source = audio_res.audio_source
        a_dur = audio_res.duration_seconds
        a_bytes = audio_res.audio_bytes
        tts_err = audio_res.friendly_err
        a_err = audio_res.audio_error
        b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

        # Derive clean error code for catalog & telemetry
        err_code = getattr(e, "error_code", None)
        if not err_code:
            err_str = str(e).lower()
            if "credit" in err_str:
                err_code = "credit_limit"
            elif "rate" in err_str or "429" in err_str:
                err_code = "rate_limit"
            elif "voice" in err_str:
                err_code = "voice_invalid"
            elif "missing_gnani" in err_str or "key is missing" in err_str:
                err_code = "gnani_key_missing"
            elif "401" in err_str or "gnani" in err_str:
                err_code = "gnani_error"
            else:
                err_code = "server_error"

        # Raw technical details logged to backend stdout/log only
        print(f"[Turn Router Error] code={err_code} detail={e}")

        catalog_key = "gnani_error" if err_code in ("gnani_error", "rate_limit") else err_code
        friendly_error = error_catalog.get_error_message(catalog_key, template_lang)

        # Persist audit log on unexpected turn error
        try:
            valid_tok_id = None
            if token_id and db.query(Token.id).filter(Token.id == token_id).first():
                valid_tok_id = token_id
            vlog = VoiceLog(
                token_id=valid_tok_id,
                transcript="",
                detected_language=template_lang,
                intent="ERROR",
                noise_label=noise_label,
                ok=False,
                error=err_code,
            )
            db.add(vlog)
            db.commit()
            broadcast_voice_log()
            broadcast_queue_change("")
            if err_code:
                from backend.app.services.monitoring import record_error
                record_error(err_code)
        except Exception:
            pass

        return TurnResponse(
            transcript="",
            detected_language=template_lang,
            reply_language="Telugu" if template_lang.startswith("te") else "English",
            intent="ERROR",
            reply_text=reply_text,
            reply_audio_base64=b64_audio,
            token=None,
            pending_confirm=False,
            error=friendly_error,
            error_code=err_code,
            limit_reason=limit_reason if err_code in ("demo_limit", "credit_limit") else None,
            limit_counts=limit_counts if err_code in ("demo_limit", "credit_limit") else None,
            demo_video_url=settings.DEMO_VIDEO_URL or None,
            audio_stats=None,
            audio_source=a_source,
            audio_duration_seconds=a_dur,
            audio_bytes=a_bytes,
            audio_error=a_err or "turn_error",
        )

    turn_resp = turn_service.process_turn(
        db=db,
        transcript=transcript,
        detected_lang=detected_lang,
        requested_lang=language,
        session_id=session_id,
        token_id=token_id,
        noise_label=noise_label,
        audio_stats=audio_stats,
        cleaned=cleaning_ran,
        raw_audio_file=raw_file,
        cleaned_audio_file=clean_file,
        stage_times=initial_stage_times,
        turn_start_time=t_turn_start,
        is_compare=is_compare_turn,
    )
    turn_resp.limit_reason = limit_reason
    turn_resp.limit_counts = limit_counts
    if settings.DEMO_VIDEO_URL:
        turn_resp.demo_video_url = settings.DEMO_VIDEO_URL
    return turn_resp


@router.get("/dev/limits")
def dev_limits(request: Request, db: Session = Depends(get_db)):
    """
    Returns current rate-limit counters and configured limits.
    Enabled only when DEV_ENDPOINTS=true.
    """
    if not settings.DEV_ENDPOINTS:
        raise HTTPException(
            status_code=403,
            detail="Developer endpoints are disabled. Set DEV_ENDPOINTS=true in backend/.env",
        )
    client_ip = credit_protection.get_client_ip(request)
    return credit_protection.get_limits_status(db=db, client_ip=client_ip)


@router.post("/dev/reset-limits")
def dev_reset_limits():
    """
    Resets in-memory per-IP and per-session voice limits.
    Enabled only when DEV_ENDPOINTS=true.
    """
    if not settings.DEV_ENDPOINTS:
        raise HTTPException(
            status_code=403,
            detail="Developer endpoints are disabled. Set DEV_ENDPOINTS=true in backend/.env",
        )
    credit_protection.reset_limits()
    return {"status": "ok", "message": "Demo rate limits reset successfully"}


@router.get("/dev/latency")
def dev_latency():
    """
    Returns median (p50) and 95th percentile (p95) per stage for the last 50 requests.
    Enabled only when DEV_ENDPOINTS=true.
    """
    if not settings.DEV_ENDPOINTS:
        raise HTTPException(
            status_code=403,
            detail="Developer endpoints are disabled. Set DEV_ENDPOINTS=true in backend/.env",
        )
    return latency_tracker.get_stats()


@router.post("/text/turn", response_model=TurnResponse)
def text_turn(
    payload: TextTurnRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handles a text-based turn with identical queue, reply, and TTS logic as /voice/turn.
    Typed requests continue working even when caps are reached; TTS comes only from cache.
    """
    client_ip = credit_protection.get_client_ip(request)
    owner_key = request.headers.get("x-owner-key") if request else None
    is_owner_req = credit_protection.is_owner(owner_key)
    allow_live_tts = credit_protection.can_make_tts_call(
        ip=client_ip,
        session_id=payload.session_id,
        is_owner_req=is_owner_req,
        db=db,
    )

    return turn_service.process_turn(
        db=db,
        transcript=payload.text,
        detected_lang=payload.language,
        requested_lang=payload.language,
        session_id=payload.session_id,
        token_id=payload.token_id,
        allow_live_tts=allow_live_tts,
    )


@router.post("/voice/retry-audio", response_model=RetryAudioResponse)
def retry_audio(
    payload: RetryAudioRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Retries speech synthesis for an existing reply text.
    Counts usage if a real Timbre TTS call is made.
    """
    client_ip = credit_protection.get_client_ip(request)
    owner_key = request.headers.get("x-owner-key") if request else None
    is_owner_req = credit_protection.is_owner(owner_key)
    allow_live_tts = credit_protection.can_make_tts_call(
        ip=client_ip,
        session_id="retry_session",
        is_owner_req=is_owner_req,
        db=db,
    )
    wav_bytes, a_source, a_dur, a_bytes, a_err = turn_service.synthesize_reply_audio(
        text=payload.text, requested_lang=payload.language, allow_live_tts=allow_live_tts
    )
    b64_audio = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None
    return RetryAudioResponse(
        reply_audio_base64=b64_audio,
        audio_source=a_source,
        audio_duration_seconds=a_dur,
        audio_bytes=a_bytes,
        audio_error=a_err,
    )


def _format_lang_label(lang_code: str) -> str:
    """Formats language codes to human-readable labels (Telugu or English, never te-IN)."""
    lower = (lang_code or "").lower().strip()
    if lower.startswith("te"):
        return "Telugu"
    if lower.startswith("en"):
        return "English"
    if lower.startswith("mix"):
        return "Mix"
    return "Telugu"


@router.get("/voice-logs", response_model=List[VoiceLogItem])
def get_voice_logs(
    limit: int = Query(20, ge=1, le=100, description="Number of recent logs to return"),
    db: Session = Depends(get_db),
):
    """Returns the latest voice interaction logs with matched token numbers."""
    logs = (
        db.query(VoiceLog, Token.number)
        .outerjoin(Token, VoiceLog.token_id == Token.id)
        .order_by(VoiceLog.created_at.desc(), VoiceLog.id.desc())
        .limit(limit)
        .all()
    )

    items = []
    for vlog, token_num in logs:
        time_str = turn_service.format_ist_time(vlog.created_at)
        items.append(
            VoiceLogItem(
                id=vlog.id,
                time=time_str,
                transcript=vlog.transcript or "",
                detected_language=_format_lang_label(vlog.detected_language),
                intent=vlog.intent or "",
                token_number=token_num,
                ok=vlog.ok,
                error=vlog.error,
                error_code=vlog.error,
            )
        )
    return items


@router.post("/voice-logs/clear", response_model=MessageResponse)
def clear_voice_logs(db: Session = Depends(get_db)):
    """Deletes all voice activity logs without affecting patient tokens."""
    db.query(VoiceLog).delete()
    db.commit()
    broadcast_voice_log()
    broadcast_queue_change("")
    return MessageResponse(message="Voice logs cleared successfully")


@router.get("/usage", response_model=UsageResponse)
def get_usage(db: Session = Depends(get_db)):
    """Returns today's and total real Gnani API call counts against credit quota."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    real_calls_today = (
        db.query(GnaniUsage)
        .filter(
            GnaniUsage.created_at >= today_start,
            GnaniUsage.cached.is_(False),
        )
        .count()
    )

    real_calls_total = (
        db.query(GnaniUsage)
        .filter(GnaniUsage.cached.is_(False))
        .count()
    )

    cached_calls = (
        db.query(GnaniUsage)
        .filter(GnaniUsage.cached.is_(True))
        .count()
    )

    stt_calls = (
        db.query(GnaniUsage)
        .filter(
            GnaniUsage.kind == "stt",
            GnaniUsage.cached.is_(False),
        )
        .count()
    )

    tts_calls = (
        db.query(GnaniUsage)
        .filter(
            GnaniUsage.kind == "tts",
            GnaniUsage.cached.is_(False),
        )
        .count()
    )

    estimated_credits = None
    if settings.GNANI_CREDITS_PER_CALL is not None:
        estimated_credits = round(real_calls_total * settings.GNANI_CREDITS_PER_CALL, 3)

    daily_cap = getattr(settings, "GNANI_DAILY_CAP", settings.GNANI_MAX_CALLS)
    reserve = getattr(settings, "GNANI_RESERVE", 40)
    return UsageResponse(
        real_calls_today=real_calls_today,
        real_calls_total=real_calls_total,
        limit=daily_cap,
        reserve=reserve,
        cached_calls=cached_calls,
        stt_calls=stt_calls,
        tts_calls=tts_calls,
        estimated_credits_used=estimated_credits,
    )


# --- Phase H: Audio Lab and Audio Compare Endpoints ---

@router.get("/debug-audio/{filename}")
def get_debug_audio(filename: str):
    """Streams a saved raw or cleaned debug audio clip if DEBUG_SAVE_AUDIO=true."""
    clean_name = os.path.basename(filename)
    file_path = audio_service.DEBUG_AUDIO_DIR / clean_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Debug audio file not found")

    media_type = "audio/wav"
    if clean_name.endswith(".webm"):
        media_type = "audio/webm"
    elif clean_name.endswith(".ogg"):
        media_type = "audio/ogg"
    elif clean_name.endswith(".m4a"):
        media_type = "audio/mp4"

    return FileResponse(file_path, media_type=media_type)


@router.post("/debug-audio/clear", response_model=MessageResponse)
def clear_debug_audio():
    """Deletes all saved debug audio recording clips."""
    audio_service.clear_debug_audio_dir()
    return MessageResponse(message="All debug audio files deleted successfully")


@router.get("/audio-lab/turns", response_model=List[AudioLabTurnItem])
def get_audio_lab_turns(db: Session = Depends(get_db)):
    """Returns the last 10 voice turns with duration, peak, rms, cleaned flag and clip links."""
    logs = (
        db.query(VoiceLog)
        .order_by(VoiceLog.created_at.desc(), VoiceLog.id.desc())
        .limit(10)
        .all()
    )
    items = []
    for log in logs:
        raw_url = None
        cleaned_url = None
        if log.raw_audio_file:
            path = audio_service.DEBUG_AUDIO_DIR / log.raw_audio_file
            if path.exists():
                raw_url = f"/debug-audio/{log.raw_audio_file}"
        if log.cleaned_audio_file:
            path = audio_service.DEBUG_AUDIO_DIR / log.cleaned_audio_file
            if path.exists():
                cleaned_url = f"/debug-audio/{log.cleaned_audio_file}"

        created_str = (
            turn_service.format_ist_time(log.created_at)
            if log.created_at
            else turn_service.format_ist_time(datetime.now(timezone.utc))
        )

        items.append(
            AudioLabTurnItem(
                id=log.id,
                transcript=log.transcript or "",
                detected_language=log.detected_language or "unknown",
                duration=round(log.duration, 2) if log.duration is not None else None,
                peak=round(log.peak, 3) if log.peak is not None else None,
                rms=round(log.rms, 3) if log.rms is not None else None,
                cleaned=log.cleaned if log.cleaned is not None else True,
                raw_audio_url=raw_url,
                cleaned_audio_url=cleaned_url,
                created_at=created_str,
                error=log.error,
            )
        )
    return items


@router.post("/voice-logs/clear", response_model=MessageResponse)
def clear_voice_logs(db: Session = Depends(get_db)):
    """Deletes all voice activity logs without affecting patient tokens."""
    db.query(VoiceLog).delete()
    db.commit()
    broadcast_queue_change("")
    return MessageResponse(message="Voice logs cleared successfully")


@router.get("/audio-compare/status")
def get_audio_compare_status(db: Session = Depends(get_db)):
    """Returns usage count and maximum allowed calls for compare mode."""
    used = credit_protection.count_compare_calls(db)
    max_calls = getattr(settings, "COMPARE_MAX_CALLS", 20)
    return {
        "used": used,
        "max": max_calls,
        "limit_reached": bool(used >= max_calls),
    }


@router.get("/audio-compare", response_model=List[AudioCompareResponse])
def get_audio_comparisons(db: Session = Depends(get_db)):
    """Returns all manual audio comparison records."""
    return (
        db.query(AudioCompare)
        .order_by(AudioCompare.created_at.desc())
        .all()
    )


@router.post("/audio-compare", response_model=AudioCompareResponse)
def create_audio_comparison(
    payload: AudioCompareCreate,
    db: Session = Depends(get_db),
):
    """Saves a manual comparison row between cleaned and raw audio."""
    row = AudioCompare(
        sentence=payload.sentence,
        cleaned_transcript=payload.cleaned_transcript or "",
        raw_transcript=payload.raw_transcript or "",
        which_better=payload.which_better or "same",
        notes=payload.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/audio-compare/export.csv")
@router.get("/audio-compare/export")
def export_audio_comparisons_csv(db: Session = Depends(get_db)):
    """Exports all comparisons in audio_compare table as a downloadable CSV."""
    rows = (
        db.query(AudioCompare)
        .order_by(AudioCompare.created_at.asc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "sentence",
        "cleaned_transcript",
        "raw_transcript",
        "which_better",
        "notes",
        "created_at",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.sentence,
            r.cleaned_transcript,
            r.raw_transcript,
            r.which_better,
            r.notes or "",
            r.created_at.isoformat() if r.created_at else "",
        ])
    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audio_compare.csv"},
    )

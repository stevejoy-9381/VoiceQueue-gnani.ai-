from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    gnani_configured: bool
    groq_configured: bool = False
    ffmpeg_found: bool
    voices_configured: bool
    voices_valid: bool = True
    invalid_voice: Optional[str] = None
    bad_voice: Optional[str] = None
    clinic_name: Optional[str] = None
    debug_save_audio: bool = False


class TokenCreate(BaseModel):
    day: str = "today"  # "today" or "tomorrow" (or YYYY-MM-DD)
    language: str = "te-IN"


class TokenResponse(BaseModel):
    id: int
    number: int
    date: str
    label: str
    language: str
    status: str
    created_at: datetime
    ahead_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QueueResponse(BaseModel):
    date: str
    total_tokens: int
    waiting_count: int
    current_in_consult: Optional[TokenResponse] = None
    tokens: list[TokenResponse]


class MessageResponse(BaseModel):
    message: str


class TextTurnRequest(BaseModel):
    text: str
    language: str = "te"  # "te", "en", "mix"
    session_id: str
    token_id: Optional[int] = None


class TurnResponse(BaseModel):
    transcript: str
    detected_language: str
    intent: str
    reply_text: str
    reply_audio_base64: Optional[str] = None  # base64 encoded WAV audio bytes or null
    token: Optional[TokenResponse] = None
    pending_confirm: bool = False
    error: Optional[str] = None
    error_code: Optional[str] = None
    audio_stats: Optional[dict[str, float]] = None
    audio_source: str = "none"  # 'cache' | 'timbre' | 'none'
    audio_duration_seconds: Optional[float] = None
    audio_bytes: Optional[int] = None
    audio_error: Optional[str] = None


class RetryAudioRequest(BaseModel):
    text: str
    language: str = "te"


class RetryAudioResponse(BaseModel):
    reply_audio_base64: Optional[str] = None
    audio_source: str = "none"
    audio_duration_seconds: Optional[float] = None
    audio_bytes: Optional[int] = None
    audio_error: Optional[str] = None


class VoiceLogItem(BaseModel):
    id: int
    time: str
    transcript: str
    detected_language: str
    intent: str
    token_number: Optional[int] = None
    ok: bool
    error: Optional[str] = None
    error_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UsageResponse(BaseModel):
    real_calls_today: int
    real_calls_total: int
    limit: int
    reserve: int = 40
    cached_calls: int
    stt_calls: int
    tts_calls: int
    estimated_credits_used: Optional[float] = None


class VoiceTestCreate(BaseModel):
    language: str  # te, en, mix
    noise: str  # quiet, fan, street
    expected_intent: str
    got_intent: str
    transcript: str
    intended_sentence: Optional[str] = None
    passed: bool
    note: Optional[str] = None


class VoiceTestResponse(BaseModel):
    id: int
    language: str
    noise: str
    expected_intent: str
    got_intent: str
    transcript: str
    intended_sentence: Optional[str] = None
    passed: bool
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudioCompareCreate(BaseModel):
    sentence: str
    cleaned_transcript: Optional[str] = ""
    raw_transcript: Optional[str] = ""
    which_better: Optional[str] = "same"  # 'cleaned', 'raw', 'same', or other note
    notes: Optional[str] = None


class AudioCompareResponse(BaseModel):
    id: int
    sentence: str
    cleaned_transcript: Optional[str] = None
    raw_transcript: Optional[str] = None
    which_better: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudioLabTurnItem(BaseModel):
    id: int
    transcript: str
    detected_language: str
    duration: Optional[float] = None
    peak: Optional[float] = None
    rms: Optional[float] = None
    cleaned: bool = True
    raw_audio_url: Optional[str] = None
    cleaned_audio_url: Optional[str] = None
    created_at: str
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NoiseSummaryItem(BaseModel):
    language: str
    noise: str
    total: int
    passed: int
    failed: int
    pass_rate: float


class VoiceTestSummary(BaseModel):
    total_trials: int
    total_passed: int
    total_failed: int
    overall_pass_rate: float
    breakdown: List[NoiseSummaryItem]


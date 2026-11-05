"""Tests for Privacy Masking and Redaction (P1-7).

Hard rules:
- Zero real Gnani calls (all STT and TTS are stubbed).
- Secrets in .env only.
- Languages: Telugu, English, Mix. No Hindi.
- No fake/mock voice data in app code.
"""

from fastapi import UploadFile
import io
import math
import struct
import wave
import pytest

from backend.app.config import settings
from backend.app.models import VoiceLog
from backend.app.routers.turn_router import clear_debug_audio, get_voice_logs, text_turn, voice_turn
from backend.app.schemas import TextTurnRequest
from backend.app.services import audio as audio_service, gnani, intent as intent_service, privacy


def _make_test_wav(duration_sec: float = 1.0, amplitude: float = 0.3) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        total_frames = int(16000 * duration_sec)
        data = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * amplitude * math.sin(2.0 * math.pi * 440.0 * (i / 16000)))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return buf.getvalue()


def _create_dummy_upload(wav_bytes: bytes, filename: str = "test.wav") -> UploadFile:
    file_obj = io.BytesIO(wav_bytes)
    return UploadFile(filename=filename, file=file_obj)


def test_phone_masking():
    """10-digit phone patterns with or without +91/0 and spaces are masked with [masked]."""
    assert privacy.mask_text("call me at 9876543210 please") == "call me at [masked] please"
    assert privacy.mask_text("phone +91 98765 43210 thanks") == "phone [masked] thanks"
    assert privacy.mask_text("number is 09876543210") == "number is [masked]"
    assert privacy.mask_text("reach me on 919876543210") == "reach me on [masked]"
    assert privacy.mask_text("tel: 98765-43210") == "tel: [masked]"


def test_aadhaar_masking():
    """12-digit Aadhaar patterns are masked with [masked]."""
    assert privacy.mask_text("my aadhaar is 123456789012") == "my aadhaar is [masked]"
    assert privacy.mask_text("aadhaar 1234 5678 9012 here") == "aadhaar [masked] here"
    assert privacy.mask_text("card 1234-5678-9012") == "card [masked]"


def test_pan_masking():
    """5-letter, 4-digit, 1-letter PAN patterns are masked with [masked]."""
    assert privacy.mask_text("pan ABCDE1234F verified") == "pan [masked] verified"
    assert privacy.mask_text("pan card abcde1234f") == "pan card [masked]"
    assert privacy.mask_text("pan ABCDE 1234 F") == "pan [masked]"


def test_email_masking():
    """Email addresses are masked with [masked]."""
    assert privacy.mask_text("email is patient.one@clinic.org") == "email is [masked]"
    assert privacy.mask_text("contact user@sub.domain.co.in please") == "contact [masked] please"


def test_name_masking_english():
    """Names up to 3 words after 'my name is', 'I am', and 'this is' are masked as [name]."""
    assert privacy.mask_text("my name is Ravi") == "my name is [name]"
    assert privacy.mask_text("my name is Ravi Kumar") == "my name is [name]"
    assert privacy.mask_text("my name is Ravi Kumar Sharma") == "my name is [name]"
    assert privacy.mask_text("my name is Ravi and I need a token") == "my name is [name] and I need a token"
    assert privacy.mask_text("I am Suresh") == "I am [name]"
    assert privacy.mask_text("I'm Ramesh") == "I'm [name]"
    assert privacy.mask_text("this is Dr Anita Roy") == "this is [name]"


def test_name_masking_telugu():
    """Names after 'naa peru' and 'nenu' in Latin and Telugu script are masked as [name]."""
    assert privacy.mask_text("naa peru Ramesh") == "naa peru [name]"
    assert privacy.mask_text("naa peru Suresh andi") == "naa peru [name] andi"
    assert privacy.mask_text("nenu Rajesh kavali") == "nenu [name] kavali"
    assert privacy.mask_text("నా పేరు రమేష్") == "నా పేరు [name]"
    assert privacy.mask_text("నేను సురేష్ కావాలి") == "నేను [name] కావాలి"


def test_stored_logs_and_feed_contain_only_masked_text(db_session, monkeypatch):
    """Voice turn stores only masked text in voice_logs and feeds masked text to dashboard."""
    def stub_stt(wav_bytes, user_lang="te", *args, **kwargs):
        return {
            "transcript": "my name is Ravi and my number is 9876543210 need token tomorrow",
            "language": "en-IN",
        }

    monkeypatch.setattr(gnani, "stt", stub_stt)

    wav_bytes = _make_test_wav(duration_sec=1.0)
    upload = _create_dummy_upload(wav_bytes)

    # 1. Voice turn executed
    res = voice_turn(
        audio=upload,
        language="en",
        session_id="privacy_test_sess",
        db=db_session,
    )

    # Patient receives their spoken transcript on their own screen
    assert res.transcript == "my name is Ravi and my number is 9876543210 need token tomorrow"

    # 2. Database record in voice_logs is strictly masked
    latest_log = db_session.query(VoiceLog).order_by(VoiceLog.id.desc()).first()
    assert latest_log is not None
    assert "9876543210" not in latest_log.transcript
    assert "Ravi" not in latest_log.transcript
    assert "[name]" in latest_log.transcript
    assert "[masked]" in latest_log.transcript

    # 3. GET /voice-logs returned for dashboard feed contains strictly masked text
    feed_items = get_voice_logs(limit=5, db=db_session)
    assert len(feed_items) > 0
    assert "9876543210" not in feed_items[0].transcript
    assert "Ravi" not in feed_items[0].transcript
    assert "[name]" in feed_items[0].transcript
    assert "[masked]" in feed_items[0].transcript


def test_groq_never_receives_unmasked_text(monkeypatch):
    """Groq fallback receives masked input and never unmasked personal details."""
    sent_prompt = None

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, headers=None, json=None):
            nonlocal sent_prompt
            sent_prompt = json["messages"][0]["content"]
            class DummyResp:
                status_code = 200
                def json(self):
                    return {"choices": [{"message": {"content": '{"intent": "BOOK", "day": "tomorrow"}'}}]}
            return DummyResp()

    monkeypatch.setattr(intent_service.httpx, "Client", DummyClient)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "ci-dummy-key")

    input_text = "my name is Ravi and phone is 9876543210"
    intent_service._call_groq_fallback(input_text)

    assert sent_prompt is not None
    assert "9876543210" not in sent_prompt
    assert "Ravi" not in sent_prompt
    assert "[name]" in sent_prompt
    assert "[masked]" in sent_prompt


def test_delete_all_debug_audio_endpoint(tmp_path, monkeypatch):
    """POST /debug-audio/clear removes all clips from debug directory."""
    test_debug_dir = tmp_path / "debug_audio"
    test_debug_dir.mkdir(parents=True, exist_ok=True)
    f1 = test_debug_dir / "clip1.wav"
    f2 = test_debug_dir / "clip2.wav"
    f1.write_bytes(b"dummy1")
    f2.write_bytes(b"dummy2")

    monkeypatch.setattr(audio_service, "DEBUG_AUDIO_DIR", test_debug_dir)

    res = clear_debug_audio()
    assert res.message == "All debug audio files deleted successfully"
    assert len(list(test_debug_dir.glob("*"))) == 0


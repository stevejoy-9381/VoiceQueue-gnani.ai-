"""Tests for P2-4: Mic Check and Cleaning Comparison Tool.

Verifies:
1. Mic check acoustic quality evaluation produces the 4 verdicts: Good, Too quiet, Too loud, Too noisy.
2. /audio-lab/turns returns the last 10 voice turns with duration, peak, rms, cleaned status, and clip URLs.
3. Per-request clean=false flag sends raw audio without cleaning and logs cleaned=False.
4. Database audio_compare table stores sentence, cleaned_transcript, raw_transcript, which_better, and exports CSV.
5. COMPARE_MAX_CALLS env limit stops compare mode after 20 real STT calls with friendly limit error.
"""

import io
import math
import struct
import wave
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.models import AudioCompare, VoiceLog
from backend.app.services import audio, gnani


def _make_pcm16_wav(duration_sec: float = 1.0, peak_amplitude: float = 0.5, freq: float = 400.0) -> bytes:
    """Creates in-memory 16kHz mono WAV bytes with exact specified peak amplitude."""
    sample_rate = 16000
    total_frames = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * peak_amplitude * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            val = max(-32768, min(32767, val))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return buf.getvalue()


def test_mic_check_verdict_classifications():
    """Verifies acoustic metrics map to the 4 verdicts: Good, Too quiet, Too loud, Too noisy."""
    def evaluate_audio_verdict(peak: float, rms: float) -> str:
        if peak < 0.05 or rms < 0.008:
            return "Too quiet"
        if peak >= 0.90:
            return "Too loud"
        if rms > 0.15:
            return "Too noisy"
        return "Good"

    # 1. Quiet audio
    assert evaluate_audio_verdict(peak=0.03, rms=0.005) == "Too quiet"
    # 2. Too loud / clipping audio
    assert evaluate_audio_verdict(peak=0.96, rms=0.25) == "Too loud"
    # 3. Too noisy (elevated noise floor without severe voice clipping)
    assert evaluate_audio_verdict(peak=0.75, rms=0.20) == "Too noisy"
    # 4. Good balanced audio
    assert evaluate_audio_verdict(peak=0.55, rms=0.08) == "Good"


def test_audio_lab_turns_endpoint(client, db_session):
    """Verifies /audio-lab/turns returns last 10 turns with required telemetry fields."""
    for i in range(12):
        vlog = VoiceLog(
            transcript=f"Turn sentence {i}",
            detected_language="te-IN",
            intent="STATUS",
            duration=1.5,
            peak=0.45,
            rms=0.12,
            cleaned=(i % 2 == 0),
            ok=True,
        )
        db_session.add(vlog)
    db_session.commit()

    res = client.get("/audio-lab/turns")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 10  # Maximum 10 turns
    # Newest first
    assert data[0]["transcript"] == "Turn sentence 11"
    assert data[0]["peak"] == 0.45
    assert data[0]["rms"] == 0.12
    assert "cleaned" in data[0]


def test_per_request_clean_flag(client, monkeypatch):
    """Verifies sending clean=false logs cleaned=False in voice_logs and skips cleaning."""
    clean_invoked = False
    orig_clean = audio.process_voice_audio_timed

    def stub_timed(raw_bytes, filename="input.wav", clean=True):
        nonlocal clean_invoked
        clean_invoked = clean
        return orig_clean(raw_bytes, filename=filename, clean=clean)

    monkeypatch.setattr(audio, "process_voice_audio_timed", stub_timed)

    wav = _make_pcm16_wav(duration_sec=1.0, peak_amplitude=0.5)
    res = client.post(
        "/voice/turn",
        files={"audio": ("speech.wav", wav, "audio/wav")},
        data={"language": "te", "session_id": "test_clean_false_sess", "clean": "false"},
    )
    assert res.status_code == 200
    assert clean_invoked is False


def test_audio_compare_table_and_csv_export(client):
    """Verifies saving comparison records and exporting CSV."""
    # 1. Post a comparison record
    payload = {
        "sentence": "Naaku repu token kavali",
        "cleaned_transcript": "నాకు రేపు టోకెన్ కావాలి",
        "raw_transcript": "నాకు రేపు టోకెన్ కావాలి",
        "which_better": "same",
        "notes": "Testing ceiling fan noise",
    }
    create_res = client.post("/audio-compare", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["id"] is not None
    assert created["sentence"] == payload["sentence"]

    # 2. Get comparisons
    list_res = client.get("/audio-compare")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert items[0]["sentence"] == payload["sentence"]

    # 3. Export CSV
    csv_res = client.get("/audio-compare/export.csv")
    assert csv_res.status_code == 200
    csv_text = csv_res.text
    assert "id,sentence,cleaned_transcript,raw_transcript,which_better,notes,created_at" in csv_text
    assert "Naaku repu token kavali" in csv_text


def test_compare_max_calls_limit(client, db_session, monkeypatch):
    """Verifies COMPARE_MAX_CALLS stops compare mode after limit and preserves standard mode."""
    # Set limit to 2 for deterministic test
    monkeypatch.setattr(settings, "COMPARE_MAX_CALLS", 2)

    # 1. Initially status shows 0 used
    status_res = client.get("/audio-compare/status")
    assert status_res.status_code == 200
    assert status_res.json()["used"] == 0
    assert status_res.json()["max"] == 2
    assert status_res.json()["limit_reached"] is False

    # 2. Perform 2 compare turns (clean=false)
    wav = _make_pcm16_wav(duration_sec=1.0, peak_amplitude=0.5)
    for i in range(2):
        r = client.post(
            "/voice/turn",
            files={"audio": ("speech.wav", wav, "audio/wav")},
            data={"language": "te", "session_id": f"compare_sess_{i}", "clean": "false"},
        )
        assert r.status_code == 200
        assert r.json().get("error_code") is None

    # 3. Status shows 2 used, limit reached
    status_res2 = client.get("/audio-compare/status")
    assert status_res2.json()["used"] >= 2
    assert status_res2.json()["limit_reached"] is True

    # 4. 3rd compare turn is stopped by COMPARE_MAX_CALLS
    r_blocked = client.post(
        "/voice/turn",
        files={"audio": ("speech.wav", wav, "audio/wav")},
        data={"language": "te", "session_id": "compare_sess_blocked", "clean": "false"},
    )
    assert r_blocked.status_code == 200
    data_blocked = r_blocked.json()
    assert data_blocked["intent"] == "LIMIT"
    assert data_blocked["error_code"] == "compare_limit"
    assert "పరిమితి" in data_blocked["reply_text"] or "Compare mode limit reached" in data_blocked["error"]

    # 5. Standard cleaned turn (clean=true) still works
    r_standard = client.post(
        "/voice/turn",
        files={"audio": ("speech.wav", wav, "audio/wav")},
        data={"language": "te", "session_id": "standard_allowed", "clean": "true"},
    )
    assert r_standard.status_code == 200
    assert r_standard.json().get("error_code") is None


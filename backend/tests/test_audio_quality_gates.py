"""Tests for Audio Quality Gates: too_short, too_long, too_quiet, no_speech, corrupt_file.

Verifies that:
1. Low quality/invalid audio is rejected locally before reaching Gnani.
2. The stubbed Gnani STT function is NEVER called when quality gates trigger.
3. Every gate returns the exact expected error_code.
4. /voice/turn returns HTTP 200 with friendly message and no server crash.
"""

import pytest
from backend.app.services import audio as audio_service, gnani
from backend.tests.audio_generator import ensure_test_audio_files


@pytest.fixture(scope="module")
def audio_files():
    """Generates and returns paths to test audio clips."""
    return ensure_test_audio_files()


def test_quality_gate_too_short(client, audio_files, monkeypatch):
    """Confirm audio < 0.5s triggers 'too_short' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["tone_0_2s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("tone_0_2s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "gate-test-short"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "too_short"
    assert "తక్కువగా" in data["reply_text"] or "short" in data["error"].lower()
    assert not stt_called, "Gnani STT should NOT have been called for too_short audio"


def test_quality_gate_too_long(client, audio_files, monkeypatch):
    """Confirm audio > 30s triggers 'too_long' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["long_35s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("long_35s.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "gate-test-long"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "too_long"
    assert "long" in data["reply_text"].lower() or "long" in data["error"].lower()
    assert not stt_called, "Gnani STT should NOT have been called for too_long audio"


def test_quality_gate_too_quiet(client, audio_files, monkeypatch):
    """Confirm audio below peak/RMS threshold triggers 'too_quiet' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["quiet_tone"].read_bytes()
    # clean=False passes raw audio directly to threshold checks without AGC dynaudnorm amplification
    resp = client.post(
        "/voice/turn",
        files={"audio": ("quiet_tone.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "gate-test-quiet", "clean": "false"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "too_quiet"
    assert "hear you" in data["reply_text"].lower() or "quiet" in data["error"].lower()
    assert not stt_called, "Gnani STT should NOT have been called for too_quiet audio"


def test_quality_gate_too_loud_clipped(client, audio_files, monkeypatch):
    """Confirm clipped/saturated audio triggers 'too_loud' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["loud_clipped"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("loud_clipped.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "gate-test-loud", "clean": "false"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "too_loud"
    assert "loud" in data["reply_text"].lower() or "loud" in data["error"].lower()
    assert not stt_called, "Gnani STT should NOT have been called for too_loud audio"


def test_quality_gate_no_speech_silence(client, audio_files, monkeypatch):
    """Confirm pure silence trimmed by silence detection triggers 'no_speech' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["silence"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("silence.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "gate-test-silence", "clean": "true"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "no_speech"
    assert not stt_called, "Gnani STT should NOT have been called for silent audio"


def test_quality_gate_no_speech_empty_file(client, audio_files, monkeypatch):
    """Confirm 0-byte audio file triggers 'no_speech' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["empty"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("empty.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "gate-test-empty"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "no_speech"
    assert not stt_called, "Gnani STT should NOT have been called for empty audio"


def test_quality_gate_corrupt_file(client, audio_files, monkeypatch):
    """Confirm corrupted audio file triggers 'corrupt_file' and STT is NOT called."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "dummy", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["corrupt"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("corrupt.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "session_id": "gate-test-corrupt"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "corrupt_file"
    assert not stt_called, "Gnani STT should NOT have been called for corrupt audio"


def test_valid_audio_passes_gates_and_calls_stt(client, audio_files, monkeypatch):
    """Confirm 1.0s speech-like audio successfully passes quality gates and reaches STT."""
    stt_called = False

    def spy_stt(*args, **kwargs):
        nonlocal stt_called
        stt_called = True
        return {"transcript": "repu token kavali", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", spy_stt)

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "gate-test-valid"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert stt_called, "Valid audio should pass quality gates and reach Gnani STT"
    assert data["intent"] == "BOOK"
    assert data["token"] is not None
    assert data["error_code"] is None


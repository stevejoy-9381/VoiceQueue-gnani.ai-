"""Pytest configuration and stubs for offline test execution inside tests/."""

import io
import math
import struct
import wave
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from backend.app.services import gnani


def _make_stub_wav(duration_sec: float = 1.0, freq: float = 330.0, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_frames = int(sample_rate * duration_sec)
        data = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * 0.2 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def stub_gnani_calls(monkeypatch):
    """
    Monkeypatches gnani.stt and gnani.tts with clean in-memory stubs
    strictly inside tests/ so unit tests execute offline without real network calls.
    """
    def stub_stt(wav_bytes: bytes, user_lang: str = "te", *args, **kwargs) -> dict:
        return {"transcript": "test transcript", "language": "te-IN"}

    def stub_tts(text: str, lang: str, voice: str | None = None) -> bytes:
        dur = max(1.0, len(text) * 0.06)
        return _make_stub_wav(duration_sec=dur)

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(gnani, "tts", stub_tts)


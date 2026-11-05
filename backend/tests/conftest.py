"""Pytest configuration and fixtures for backend/tests.

Guarantees 100% offline, repeatable execution:
- Uses in-memory SQLite database.
- Monkeypatches all external Gnani STT and TTS calls.
- Provides isolated FastAPI TestClient with DB dependency override.
- Never prints or commits real secrets; uses dummy 'ci-dummy-key'.
"""

import io
import math
import struct
import wave
import sys
from pathlib import Path

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config import settings
from backend.app.db import Base, get_db
from backend.app.main import app
from backend.app.services import gnani

# In-memory SQLite DB for tests
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _make_stub_wav(duration_sec: float = 0.2, freq: float = 330.0, sample_rate: int = 16000) -> bytes:
    """Creates a deterministic valid PCM 16kHz mono WAV byte string."""
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
def block_outbound_network(monkeypatch):
    """
    Strict socket firewall fixture: blocks any outbound non-loopback network calls.
    Allows loopback (127.0.0.1, localhost, ::1) for in-process TestClient communication.
    Fails immediately if any test attempts to access the external internet or Gnani.
    """
    import socket
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
        if host in ("127.0.0.1", "localhost", "::1"):
            return orig_connect(self, address)
        raise RuntimeError(f"Outbound network access blocked by test harness: {address}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up isolated in-memory DB and ensures NO real Gnani calls are made.
    Uses 'ci-dummy-key' for Gnani and Groq keys.
    """
    # Create DB schema
    Base.metadata.create_all(bind=test_engine)

    # Set dummy secrets
    monkeypatch.setattr(settings, "GNANI_API_KEY", "ci-dummy-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "ci-dummy-groq")
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    # Stub out Gnani STT and TTS
    def stub_stt(wav_bytes: bytes, user_lang: str = "te", *args, **kwargs) -> dict:
        return {"transcript": "repu token kavali", "language": "te-IN"}

    def stub_tts(text: str, lang: str, voice: str | None = None) -> bytes:
        dur = max(1.0, len(text) * 0.06)
        return _make_stub_wav(duration_sec=dur)

    monkeypatch.setattr(gnani, "stt", stub_stt)
    monkeypatch.setattr(gnani, "tts", stub_tts)
    monkeypatch.setattr(gnani, "SessionLocal", TestingSessionLocal)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provides a fresh transactional database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Provides a FastAPI TestClient bound to the isolated in-memory DB."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

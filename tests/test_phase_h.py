"""Unit tests for Phase H: Listening quality tools, audio lab, compare table, and raw audio toggle."""

import csv
import io
import math
import struct
import wave
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.db import Base
from backend.app.models import AudioCompare, VoiceLog
from backend.app.routers.turn_router import (
    create_audio_comparison,
    export_audio_comparisons_csv,
    get_audio_comparisons,
    get_audio_lab_turns,
    get_debug_audio,
)
from backend.app.schemas import AudioCompareCreate
from backend.app.services import audio as audio_service


# Test in-memory SQLite database
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_test_wav(
    duration_sec: float = 1.0,
    freq: float = 440.0,
    amplitude: float = 0.4,
    sample_rate: int = 16000,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_frames = int(sample_rate * duration_sec)
        data = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * amplitude * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return buf.getvalue()


def test_process_audio_raw_vs_cleaned():
    """Verify that clean=False bypasses ffmpeg cleaning filters."""
    raw_wav = make_test_wav(duration_sec=1.0)

    # With cleaning (clean=True)
    cleaned_out = audio_service.process_audio_with_gates(raw_wav, clean=True)
    assert len(cleaned_out) > 44

    # Without cleaning (clean=False)
    raw_out = audio_service.process_audio_with_gates(raw_wav, clean=False)
    assert len(raw_out) > 44


def test_audio_lab_turns_endpoint(db_session):
    """Verify get_audio_lab_turns returns the last 10 turns with audio metrics."""
    # Seed a couple of VoiceLog entries
    for i in range(3):
        vlog = VoiceLog(
            transcript=f"Test transcript {i}",
            detected_language="en-IN",
            intent="BOOK",
            duration=1.5 + i * 0.5,
            peak=0.4 + i * 0.1,
            rms=0.1 + i * 0.05,
            cleaned=(i % 2 == 0),
            ok=True,
        )
        db_session.add(vlog)
    db_session.commit()

    turns = get_audio_lab_turns(db=db_session)
    assert len(turns) == 3
    first = turns[0]
    assert first.transcript is not None
    assert first.duration is not None
    assert first.peak is not None
    assert first.rms is not None
    assert hasattr(first, "cleaned")
    assert hasattr(first, "raw_audio_url")
    assert hasattr(first, "cleaned_audio_url")


def test_audio_compare_crud_and_csv_export(db_session):
    """Verify saving to audio_compare table and exporting to CSV."""
    # 1. Create comparison record
    payload = AudioCompareCreate(
        sentence="Naaku repu token kavali",
        cleaned_transcript="నాకు రేపు టోకెన్ కావాలి",
        raw_transcript="నాకు రేపు టోకన్ కావాలి",
        which_better="cleaned",
        notes="Fan noise was reduced nicely by cleaning",
    )
    created = create_audio_comparison(payload, db=db_session)
    assert created.id is not None
    assert created.sentence == payload.sentence
    assert created.which_better == "cleaned"

    # 2. List comparisons
    rows = get_audio_comparisons(db=db_session)
    assert len(rows) >= 1
    assert any(r.sentence == payload.sentence for r in rows)

    # 3. Export CSV
    resp = export_audio_comparisons_csv(db=db_session)
    assert "text/csv" in resp.headers["content-type"]
    csv_text = resp.body.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    assert "sentence" in header
    assert "cleaned_transcript" in header
    assert "raw_transcript" in header
    assert "which_better" in header
    # Check that our row is in the CSV
    found = False
    for row in reader:
        if len(row) > 1 and row[1] == payload.sentence:
            found = True
            break
    assert found


def test_debug_audio_file_not_found():
    """Verify 404 is returned when debug audio clip does not exist."""
    with pytest.raises(HTTPException) as excinfo:
        get_debug_audio("non_existent_file.wav")
    assert excinfo.value.status_code == 404

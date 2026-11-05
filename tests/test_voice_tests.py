"""Tests for Phase 8: Voice test logging, telemetry summary, CSV export, and text test runner."""

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.routers.voice_test_router import (
    export_voice_tests_csv,
    get_voice_tests_summary,
    list_voice_tests,
    record_voice_test,
)
from backend.app.schemas import VoiceTestCreate
from scripts.run_text_tests import run_tests


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_record_and_list_voice_tests(in_memory_db):
    test_item = VoiceTestCreate(
        language="te",
        noise="fan",
        expected_intent="BOOK",
        got_intent="BOOK",
        transcript="repu token kavali",
        passed=True,
        note="Fan running on medium speed",
    )
    created = record_voice_test(test_item, db=in_memory_db)
    assert created.id is not None
    assert created.language == "te"
    assert created.noise == "fan"
    assert created.passed is True

    items = list_voice_tests(db=in_memory_db)
    assert len(items) == 1
    assert items[0].transcript == "repu token kavali"


def test_voice_tests_summary_and_export(in_memory_db):
    # Add multiple test rows
    record_voice_test(
        VoiceTestCreate(
            language="te",
            noise="quiet",
            expected_intent="BOOK",
            got_intent="BOOK",
            transcript="repu token kavali",
            passed=True,
        ),
        db=in_memory_db,
    )
    record_voice_test(
        VoiceTestCreate(
            language="te",
            noise="street",
            expected_intent="STATUS",
            got_intent="UNKNOWN",
            transcript="traffic noise muffled words",
            passed=False,
            note="Loud motorcycle passed",
        ),
        db=in_memory_db,
    )
    record_voice_test(
        VoiceTestCreate(
            language="en",
            noise="quiet",
            expected_intent="CANCEL",
            got_intent="CANCEL",
            transcript="cancel my token",
            passed=True,
        ),
        db=in_memory_db,
    )

    summary = get_voice_tests_summary(db=in_memory_db)
    assert summary.total_trials == 3
    assert summary.total_passed == 2
    assert summary.total_failed == 1
    assert summary.overall_pass_rate == round((2 / 3 * 100), 1)

    # Check export
    resp = export_voice_tests_csv(db=in_memory_db)
    assert resp.status_code == 200
    assert resp.media_type == "text/csv"
    csv_text = resp.body.decode("utf-8")
    assert "Expected Intent" in csv_text
    assert "traffic noise muffled words" in csv_text
    assert "FAIL" in csv_text
    assert "PASS" in csv_text


def test_offline_text_benchmark_accuracy():
    total, passed, misses = run_tests()
    assert total == 45
    assert passed == 45
    assert len(misses) == 0


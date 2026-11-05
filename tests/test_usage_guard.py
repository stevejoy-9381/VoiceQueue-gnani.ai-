"""Tests for usage tracking, credits meter calculation, and quota safety guard."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.db import Base
from backend.app.models import GnaniUsage
from backend.app.routers.turn_router import get_usage, text_turn
from backend.app.schemas import TextTurnRequest
from backend.app.services.gnani import CreditLimitError, _check_daily_credit_limit

# Test Database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
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


def test_get_usage_empty(db_session):
    res = get_usage(db=db_session)
    assert res.real_calls_today == 0
    assert res.real_calls_total == 0
    assert res.limit == settings.GNANI_MAX_CALLS
    assert res.cached_calls == 0
    assert res.stt_calls == 0
    assert res.tts_calls == 0


def test_get_usage_with_calls_and_estimated_credits(db_session):
    now = datetime.now(timezone.utc)
    # Add 2 real STT calls and 1 cached TTS call
    u1 = GnaniUsage(kind="stt", cached=False, ok=True, created_at=now)
    u2 = GnaniUsage(kind="stt", cached=False, ok=True, created_at=now)
    u3 = GnaniUsage(kind="tts", cached=True, ok=True, created_at=now)
    db_session.add_all([u1, u2, u3])
    db_session.commit()

    # Without credits per call
    res = get_usage(db=db_session)
    assert res.real_calls_today == 2
    assert res.real_calls_total == 2
    assert res.cached_calls == 1
    assert res.stt_calls == 2
    assert res.tts_calls == 0

    # With credits per call
    old_credits = settings.GNANI_CREDITS_PER_CALL
    try:
        settings.GNANI_CREDITS_PER_CALL = 0.05
        res_with_cr = get_usage(db=db_session)
        assert res_with_cr.estimated_credits_used == 0.1
    finally:
        settings.GNANI_CREDITS_PER_CALL = old_credits


def test_credit_limit_guard_blocks_third_call(db_session):
    old_max = settings.GNANI_MAX_CALLS
    try:
        settings.GNANI_MAX_CALLS = 2
        now = datetime.now(timezone.utc)

        # First 2 calls logged
        db_session.add(GnaniUsage(kind="stt", cached=False, ok=True, created_at=now))
        db_session.add(GnaniUsage(kind="tts", cached=False, ok=True, created_at=now))
        db_session.commit()

        # Direct guard check raises CreditLimitError
        with pytest.raises(CreditLimitError, match="credit limit reached: 2/2"):
            _check_daily_credit_limit(db_session)

        # Text turns continue to function even when limit is reached
        req = TextTurnRequest(
            text="Ek token chahiye",
            language="hi",
            session_id="test_typed_still_works",
        )
        res = text_turn(payload=req, db=db_session)
        assert res.intent == "BOOK"
        assert res.token is not None
        assert res.error is None
    finally:
        settings.GNANI_MAX_CALLS = old_max

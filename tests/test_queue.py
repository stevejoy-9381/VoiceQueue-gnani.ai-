"""Pytest suite for Queue service logic and REST endpoints."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.schemas import TokenCreate
from backend.app.services import queue_service
from backend.app.routers import queue_router

# In-memory SQLite database for test isolation
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


def test_token_numbering_starts_at_one_per_date(db_session):
    # Today tokens
    t1 = queue_service.book(db_session, day="today", language="te-IN")
    t2 = queue_service.book(db_session, day="today", language="en-IN")
    assert t1.number == 1
    assert t2.number == 2
    assert t1.date == t2.date

    # Tomorrow tokens should restart at 1
    t_tomorrow = queue_service.book(db_session, day="tomorrow", language="te-IN")
    assert t_tomorrow.number == 1
    assert t_tomorrow.date != t1.date


def test_queue_position_math(db_session):
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")
    t3 = queue_service.book(db_session, day="today")

    assert queue_service.position(db_session, t1.id) == 0
    assert queue_service.position(db_session, t2.id) == 1
    assert queue_service.position(db_session, t3.id) == 2


def test_cancel_removes_from_queue_and_updates_position(db_session):
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")
    t3 = queue_service.book(db_session, day="today")

    # Cancel t1
    cancelled_t1 = queue_service.cancel(db_session, t1.id)
    assert cancelled_t1.status == "cancelled"

    # t2 was at position 1, now has 0 ahead
    assert queue_service.position(db_session, t2.id) == 0
    # t3 was at position 2, now has 1 ahead
    assert queue_service.position(db_session, t3.id) == 1


def test_done_token_cannot_be_cancelled(db_session):
    t1 = queue_service.book(db_session, day="today")
    queue_service.mark(db_session, t1.id, "done")

    with pytest.raises(ValueError, match="A done token cannot be cancelled"):
        queue_service.cancel(db_session, t1.id)


def test_call_next_advances_queue(db_session):
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")

    # Call next -> t1 becomes in_consult
    first = queue_service.call_next(db_session, target_date_str="today")
    assert first is not None
    assert first.id == t1.id
    assert first.status == "in_consult"

    # Call next again -> t1 becomes done, t2 becomes in_consult
    second = queue_service.call_next(db_session, target_date_str="today")
    assert second is not None
    assert second.id == t2.id
    assert second.status == "in_consult"

    db_session.refresh(t1)
    assert t1.status == "done"

    # Call next when queue is empty -> returns None
    third = queue_service.call_next(db_session, target_date_str="today")
    assert third is None


def test_rest_endpoints_flow(db_session):
    # 1. Reset demo
    res_reset = queue_router.reset_demo_data(db=db_session)
    assert res_reset.message == "Demo queue reset successfully."

    # 2. Seed demo
    seeds = queue_router.seed_demo_data(day="today", db=db_session)
    assert len(seeds) == 6
    assert seeds[0].status == "in_consult"
    assert seeds[1].status == "waiting"

    # 3. Check queue
    queue_data = queue_router.get_queue(day="today", db=db_session)
    assert queue_data.total_tokens == 6
    assert queue_data.waiting_count == 5

    # 4. Book a new token via REST router
    new_token = queue_router.book_token(TokenCreate(day="today", language="te-IN"), db=db_session)
    assert new_token.number == 7
    # 1 in_consult + 5 waiting ahead = 6 ahead
    assert new_token.ahead_count == 6

    # 5. Cancel token 2
    tok2_id = seeds[1].id
    cancelled_tok = queue_router.cancel_token(token_id=tok2_id, db=db_session)
    assert cancelled_tok.status == "cancelled"

    # 6. Re-check token 7 position (ahead count dropped by 1)
    tok7 = queue_router.get_token(token_id=new_token.id, db=db_session)
    assert tok7.ahead_count == 5

    # 7. Advance queue
    next_tok = queue_router.call_next_token(day="today", db=db_session)
    assert next_tok is not None
    # tok 2 was cancelled, so next waiting was tok 3
    assert next_tok.number == 3
    assert next_tok.status == "in_consult"

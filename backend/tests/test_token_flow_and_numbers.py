"""Unit tests verifying single source of truth for booked tokens, number word matching, and flow integrity.

Zero Gnani calls: All tests use in-memory SQLite and stubs.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import Token
from backend.app.services import queue_service, turn_service
from backend.app.services.number_words import to_words


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_number_words_equal_token_number_for_target_numbers(db_session):
    """(c) Number words in reply equal token number in response for 11, 13, 16, 17 in both Telugu and English."""
    target_numbers = [11, 13, 16, 17]

    for target_num in target_numbers:
        # Pre-seed database up to target_num - 1
        db_session.query(Token).delete()
        db_session.commit()
        for i in range(1, target_num):
            t = Token(
                number=i,
                date=queue_service.resolve_date("tomorrow"),
                label=f"Patient {i}",
                language="te-IN",
                status="waiting",
            )
            db_session.add(t)
        db_session.commit()

        # 1. Test in Telugu
        resp_te = turn_service.process_turn(
            db=db_session,
            transcript="repu token kavali",
            detected_lang="te",
            requested_lang="te",
            session_id=f"sess-te-{target_num}",
            allow_live_tts=False,
        )
        assert resp_te.token is not None
        assert resp_te.token.number == target_num

        word_te = to_words(target_num, "te-IN")
        assert word_te in resp_te.reply_text, f"Expected Telugu word '{word_te}' in '{resp_te.reply_text}'"
        assert str(target_num) in resp_te.english_translation
        assert "నంబర్" in resp_te.reply_text

        # 2. Reset and test in English
        db_session.query(Token).delete()
        db_session.commit()
        for i in range(1, target_num):
            t = Token(
                number=i,
                date=queue_service.resolve_date("tomorrow"),
                label=f"Patient {i}",
                language="en-IN",
                status="waiting",
            )
            db_session.add(t)
        db_session.commit()

        resp_en = turn_service.process_turn(
            db=db_session,
            transcript="I need a token for tomorrow",
            detected_lang="en",
            requested_lang="en",
            session_id=f"sess-en-{target_num}",
            allow_live_tts=False,
        )
        assert resp_en.token is not None
        assert resp_en.token.number == target_num

        word_en = to_words(target_num, "en-IN")
        assert word_en in resp_en.reply_text.lower(), f"Expected English word '{word_en}' in '{resp_en.reply_text}'"


def test_two_bookings_in_a_row_returns_new_token_never_old(db_session):
    """(a) Two bookings in a row in Telugu and English: card/response always returns the newest token."""
    # First booking: Telugu
    resp1 = turn_service.process_turn(
        db=db_session,
        transcript="repu token kavali",
        detected_lang="te",
        requested_lang="te",
        session_id="sess-consecutive-1",
        token_id=None,
        allow_live_tts=False,
    )
    assert resp1.token is not None
    tok1_id = resp1.token.id
    tok1_num = resp1.token.number
    assert tok1_num == 1

    # Second booking: English, client sends the old token_id
    resp2 = turn_service.process_turn(
        db=db_session,
        transcript="I need a token for tomorrow",
        detected_lang="en",
        requested_lang="en",
        session_id="sess-consecutive-1",
        token_id=tok1_id,
        allow_live_tts=False,
    )
    assert resp2.token is not None
    tok2_id = resp2.token.id
    tok2_num = resp2.token.number

    # The returned token MUST be the new one, never the old one
    assert tok2_id != tok1_id
    assert tok2_num == tok1_num + 1
    assert resp2.token.number == 2
    assert "two" in resp2.reply_text.lower()


def test_status_and_cancel_refer_to_correct_token(db_session):
    """(d) STATUS and CANCEL show and refer to the correct token."""
    # Book two tokens
    tok1 = queue_service.book(db_session, day="today", language="te-IN")
    tok2 = queue_service.book(db_session, day="today", language="te-IN")

    # Status query for tok2 specifically
    resp_status = turn_service.process_turn(
        db=db_session,
        transcript="naa token status",
        detected_lang="te",
        requested_lang="te",
        session_id="sess-status-test",
        token_id=tok2.id,
        allow_live_tts=False,
    )
    assert resp_status.token is not None
    assert resp_status.token.id == tok2.id
    assert resp_status.token.number == tok2.number

    # Cancel initiation for tok1
    resp_cancel = turn_service.process_turn(
        db=db_session,
        transcript="token cancel cheyandi",
        detected_lang="te",
        requested_lang="te",
        session_id="sess-cancel-test",
        token_id=tok1.id,
        allow_live_tts=False,
    )
    assert resp_cancel.pending_confirm is True
    assert resp_cancel.token is not None
    assert resp_cancel.token.id == tok1.id
    assert resp_cancel.token.number == tok1.number
    assert str(tok1.number) in resp_cancel.english_translation or to_words(tok1.number, "te-IN") in resp_cancel.reply_text


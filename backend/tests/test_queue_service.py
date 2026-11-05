"""Phase T1 - Backend Queue Tests.

Tests:
1. Numbering restarts per date.
2. Queue position math.
3. Cancel token and position update.
4. Call next advances queue (in_consult -> done, waiting -> in_consult).
5. Mark done.
6. Mark no_show.
7. Cannot cancel a done token.
8. Today and tomorrow queues are strictly separate.
9. Seed and reset demo queue.
"""

import pytest
from backend.app.services import queue_service


def test_queue_numbering_restarts_per_date(db_session):
    """Token numbers start at 1 for each date and increment monotonically."""
    # Book for today
    t1_today = queue_service.book(db_session, day="today", language="te-IN")
    t2_today = queue_service.book(db_session, day="today", language="en-IN")
    assert t1_today.number == 1
    assert t2_today.number == 2
    assert t1_today.date == t2_today.date

    # Book for tomorrow -> must restart at 1
    t1_tomorrow = queue_service.book(db_session, day="tomorrow", language="te-IN")
    t2_tomorrow = queue_service.book(db_session, day="tomorrow", language="en-IN")
    assert t1_tomorrow.number == 1
    assert t2_tomorrow.number == 2
    assert t1_tomorrow.date != t1_today.date
    assert t1_tomorrow.date == t2_tomorrow.date


def test_queue_position_math(db_session):
    """Position returns count of waiting/in_consult tokens ahead on same date."""
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")
    t3 = queue_service.book(db_session, day="today")

    assert queue_service.position(db_session, t1.id) == 0
    assert queue_service.position(db_session, t2.id) == 1
    assert queue_service.position(db_session, t3.id) == 2


def test_queue_cancel_updates_positions(db_session):
    """Cancelling a waiting token removes it from queue and shifts ahead counts."""
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")
    t3 = queue_service.book(db_session, day="today")

    cancelled = queue_service.cancel(db_session, t2.id)
    assert cancelled.status == "cancelled"

    assert queue_service.position(db_session, t1.id) == 0
    assert queue_service.position(db_session, t3.id) == 1


def test_cannot_cancel_done_token(db_session):
    """Cancelling a token with status 'done' raises ValueError."""
    t1 = queue_service.book(db_session, day="today")
    queue_service.mark(db_session, t1.id, "done")

    with pytest.raises(ValueError, match="A done token cannot be cancelled"):
        queue_service.cancel(db_session, t1.id)


def test_call_next_advances_queue(db_session):
    """call_next moves next waiting token to in_consult and marks existing in_consult as done."""
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")

    # First call_next: t1 becomes in_consult
    first = queue_service.call_next(db_session, target_date_str="today")
    assert first is not None
    assert first.id == t1.id
    assert first.status == "in_consult"

    # Second call_next: t1 becomes done, t2 becomes in_consult
    second = queue_service.call_next(db_session, target_date_str="today")
    assert second is not None
    assert second.id == t2.id
    assert second.status == "in_consult"

    db_session.refresh(t1)
    assert t1.status == "done"

    # Third call_next: no more waiting patients -> returns None, t2 becomes done
    third = queue_service.call_next(db_session, target_date_str="today")
    assert third is None
    db_session.refresh(t2)
    assert t2.status == "done"


def test_mark_done_and_no_show(db_session):
    """mark() updates token status to 'done' or 'no_show', and rejects invalid statuses."""
    t1 = queue_service.book(db_session, day="today")
    t2 = queue_service.book(db_session, day="today")

    done_tok = queue_service.mark(db_session, t1.id, "done")
    assert done_tok.status == "done"

    noshow_tok = queue_service.mark(db_session, t2.id, "no_show")
    assert noshow_tok.status == "no_show"

    with pytest.raises(ValueError, match="Invalid status"):
        queue_service.mark(db_session, t1.id, "invalid_status")


def test_today_and_tomorrow_are_separate(db_session):
    """Tokens, positions, and listings for today and tomorrow do not interfere."""
    t_today1 = queue_service.book(db_session, day="today")
    t_today2 = queue_service.book(db_session, day="today")
    t_tom1 = queue_service.book(db_session, day="tomorrow")

    today_list = queue_service.list_queue(db_session, "today")
    tomorrow_list = queue_service.list_queue(db_session, "tomorrow")

    assert len(today_list) == 2
    assert len(tomorrow_list) == 1
    assert today_list[0].id == t_today1.id
    assert tomorrow_list[0].id == t_tom1.id

    # Position math is per date
    assert queue_service.position(db_session, t_tom1.id) == 0


def test_seed_and_reset_demo(db_session):
    """seed_demo creates 6 demo patients; reset_demo clears all tokens."""
    seeds = queue_service.seed_demo(db_session, day="today")
    assert len(seeds) == 6
    assert seeds[0].status == "in_consult"
    assert seeds[0].label == "Demo Patient 1"
    assert seeds[1].status == "waiting"

    queue = queue_service.list_queue(db_session, "today")
    assert len(queue) == 6

    queue_service.reset_demo(db_session)
    empty_queue = queue_service.list_queue(db_session, "today")
    assert len(empty_queue) == 0

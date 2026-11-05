"""Tests for the interactive cancel confirmation flow and timeout expiry.

Flows tested:
1. User requests cancel -> pending state entered (pending_confirm=True).
2. User confirms with 'YES' -> Token cancelled, queue notified, pending cleared.
3. User declines with 'NO' -> Cancellation aborted, token remains waiting, pending cleared.
4. Expiry after 60s -> Clock faked +61s; pending state automatically expires, 'YES' does not cancel.
"""

import time
import pytest
from backend.app.models import Token
from backend.app.services import queue_service, turn_service


@pytest.fixture(autouse=True)
def clean_pending_state():
    """Ensure in-memory pending state is clear before and after each test."""
    turn_service._pending_actions.clear()
    yield
    turn_service._pending_actions.clear()


def test_cancel_confirmation_yes_cancels_token(client, db_session):
    """Cancel request followed by YES cancels the active token."""
    # 1. Book a token first
    tok = queue_service.book(db_session, day="today", language="te-IN")
    assert tok.status == "waiting"

    session_id = "sess-cancel-yes"

    # 2. User says 'cancel my token'
    resp1 = client.post(
        "/text/turn",
        json={"text": "రద్దు చేయండి", "language": "te", "session_id": session_id, "token_id": tok.id},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["pending_confirm"] is True
    assert data1["token"]["id"] == tok.id
    assert "రద్దు" in data1["reply_text"] or "sure" in data1["reply_text"].lower()

    # 3. User says 'yes'
    resp2 = client.post(
        "/text/turn",
        json={"text": "అవును", "language": "te", "session_id": session_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["pending_confirm"] is False
    assert "రద్దు చేయబడింది" in data2["reply_text"] or "cancelled" in data2["reply_text"].lower()

    # 4. Verify DB status
    db_session.refresh(tok)
    assert tok.status == "cancelled"
    assert turn_service._get_pending(session_id) is None


def test_cancel_confirmation_no_aborts_cancellation(client, db_session):
    """Cancel request followed by NO preserves the active token."""
    tok = queue_service.book(db_session, day="today", language="en-IN")
    assert tok.status == "waiting"

    session_id = "sess-cancel-no"

    # User says 'cancel appointment'
    resp1 = client.post(
        "/text/turn",
        json={"text": "cancel my token", "language": "en", "session_id": session_id, "token_id": tok.id},
    )
    assert resp1.status_code == 200
    assert resp1.json()["pending_confirm"] is True

    # User says 'no'
    resp2 = client.post(
        "/text/turn",
        json={"text": "no don't cancel", "language": "en", "session_id": session_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["pending_confirm"] is False
    assert "cancellation was cancelled" in data2["reply_text"].lower() or "active" in data2["reply_text"].lower()

    # Verify DB status remains waiting
    db_session.refresh(tok)
    assert tok.status == "waiting"
    assert turn_service._get_pending(session_id) is None


def test_cancel_confirmation_expires_after_60_seconds(client, db_session, monkeypatch):
    """Confirm pending cancel expires after 60 seconds when clock advances."""
    tok = queue_service.book(db_session, day="today", language="en-IN")
    session_id = "sess-cancel-expire"

    # User initiates cancel at time t0
    start_time = 1700000000.0
    monkeypatch.setattr(time, "time", lambda: start_time)

    resp1 = client.post(
        "/text/turn",
        json={"text": "cancel token", "language": "en", "session_id": session_id, "token_id": tok.id},
    )
    assert resp1.status_code == 200
    assert resp1.json()["pending_confirm"] is True

    # Fast forward clock by 65 seconds (> 60s timeout)
    monkeypatch.setattr(time, "time", lambda: start_time + 65.0)

    # User says 'yes' after timeout expired
    resp2 = client.post(
        "/text/turn",
        json={"text": "yes", "language": "en", "session_id": session_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Because pending expired, 'yes' is not treated as a confirmation for cancellation
    assert data2["pending_confirm"] is False
    db_session.refresh(tok)
    assert tok.status == "waiting", "Token should NOT be cancelled after timeout expiry!"

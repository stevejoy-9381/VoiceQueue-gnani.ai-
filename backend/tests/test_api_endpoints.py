"""Phase T1 - FastAPI REST Endpoints Success & Error Paths Tests.

Uses FastAPI TestClient to test:
1. POST /tokens: success path (201) and error path (400 on invalid day).
2. GET /tokens/{id}: success path (200) and 404 on unknown token.
3. POST /tokens/{id}/cancel: success path (200), 404 on unknown token, 400 on already done token.
4. GET /queue: success path (200) and 400 on invalid day.
5. POST /queue/next: success path (200), null on empty, 400 on invalid day.
6. POST /queue/{id}/done: success path (200) and 404 on unknown token.
7. POST /queue/{id}/no-show: success path (200) and 404 on unknown token.
8. POST /demo/reset and POST /demo/seed.
9. POST /text/turn: booking, status, cancel, empty text.
10. POST /voice/turn: quality gates (too quiet/silent audio rejection).
11. Telemetry & Lab endpoints: /usage, /voice-logs, /audio-lab/turns, /audio-compare, /voice-tests.
"""

import io
import pytest
from backend.app.schemas import TokenCreate


def test_book_token_success_and_invalid_day(client):
    """POST /tokens creates a token on valid day; returns 400 on invalid day."""
    # Success path
    res = client.post("/tokens", json={"day": "today", "language": "te-IN"})
    assert res.status_code == 201
    data = res.json()
    assert data["number"] == 1
    assert data["status"] == "waiting"

    # Tomorrow booking
    res_tom = client.post("/tokens", json={"day": "tomorrow", "language": "en-IN"})
    assert res_tom.status_code == 201
    assert res_tom.json()["number"] == 1

    # Error path: invalid day string
    res_err = client.post("/tokens", json={"day": "not-a-real-day", "language": "en-IN"})
    assert res_err.status_code == 400
    assert "Invalid day" in res_err.json()["detail"]


def test_get_token_success_and_404(client):
    """GET /tokens/{id} returns token or 404 for unknown token."""
    # Book a token
    tok_res = client.post("/tokens", json={"day": "today"}).json()
    tok_id = tok_res["id"]

    # Success path
    res = client.get(f"/tokens/{tok_id}")
    assert res.status_code == 200
    assert res.json()["id"] == tok_id

    # Error path: unknown token
    res_404 = client.get("/tokens/999999")
    assert res_404.status_code == 404
    assert "Token not found" in res_404.json()["detail"]


def test_cancel_token_success_404_and_invalid_state(client):
    """POST /tokens/{id}/cancel handles success, 404 unknown, and 400 on done token."""
    # Unknown token -> 404
    res_404 = client.post("/tokens/999999/cancel")
    assert res_404.status_code == 404

    # Valid token cancel
    tok = client.post("/tokens", json={"day": "today"}).json()
    res = client.post(f"/tokens/{tok['id']}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # Invalid state change: cannot cancel a done token -> 400
    tok2 = client.post("/tokens", json={"day": "today"}).json()
    client.post(f"/queue/{tok2['id']}/done")
    res_done_cancel = client.post(f"/tokens/{tok2['id']}/cancel")
    assert res_done_cancel.status_code == 400
    assert "cannot be cancelled" in res_done_cancel.json()["detail"]


def test_queue_listing_and_invalid_day(client):
    """GET /queue returns queue for valid date; 400 on invalid day."""
    res = client.get("/queue?day=today")
    assert res.status_code == 200
    data = res.json()
    assert "total_tokens" in data
    assert "waiting_count" in data

    res_err = client.get("/queue?day=yesterday-invalid")
    assert res_err.status_code == 400


def test_call_next_success_and_empty(client):
    """POST /queue/next advances waiting token or returns null when queue empty."""
    # When empty
    res_empty = client.post("/queue/next?day=today")
    assert res_empty.status_code == 200
    assert res_empty.json() is None

    # After booking
    tok = client.post("/tokens", json={"day": "today"}).json()
    res_next = client.post("/queue/next?day=today")
    assert res_next.status_code == 200
    assert res_next.json()["id"] == tok["id"]
    assert res_next.json()["status"] == "in_consult"

    # Invalid day -> 400
    res_inv = client.post("/queue/next?day=bad-day")
    assert res_inv.status_code == 400


def test_mark_done_and_no_show_endpoints(client):
    """POST /queue/{id}/done and /no-show update status; return 404 for unknown token."""
    tok = client.post("/tokens", json={"day": "today"}).json()
    tok_id = tok["id"]

    res_done = client.post(f"/queue/{tok_id}/done")
    assert res_done.status_code == 200
    assert res_done.json()["status"] == "done"

    tok2 = client.post("/tokens", json={"day": "today"}).json()
    res_noshow = client.post(f"/queue/{tok2['id']}/no-show")
    assert res_noshow.status_code == 200
    assert res_noshow.json()["status"] == "no_show"

    # 404 on unknown tokens
    assert client.post("/queue/999999/done").status_code == 404
    assert client.post("/queue/999999/no-show").status_code == 404


def test_demo_seed_and_reset_endpoints(client):
    """POST /demo/seed seeds 6 tokens; POST /demo/reset clears all."""
    res_seed = client.post("/demo/seed?day=today")
    assert res_seed.status_code == 200
    assert len(res_seed.json()) == 6

    # Invalid day seed -> 400
    assert client.post("/demo/seed?day=bad-date").status_code == 400

    res_reset = client.post("/demo/reset")
    assert res_reset.status_code == 200
    assert "reset successfully" in res_reset.json()["message"]

    res_q = client.get("/queue?day=today")
    assert res_q.json()["total_tokens"] == 0


def test_text_turn_endpoint(client):
    """POST /text/turn processes text turns for booking, status, and empty text."""
    # 1. Booking turn
    res_book = client.post(
        "/text/turn",
        json={"text": "repu token kavali", "language": "te", "session_id": "test_sess_1"},
    )
    assert res_book.status_code == 200
    data_book = res_book.json()
    assert data_book["intent"] == "BOOK"
    assert data_book["token"] is not None

    # 2. Status turn
    res_status = client.post(
        "/text/turn",
        json={"text": "status please", "language": "en", "session_id": "test_sess_1", "token_id": data_book["token"]["id"]},
    )
    assert res_status.status_code == 200
    assert res_status.json()["intent"] == "STATUS"

    # 3. Empty text -> say again prompt
    res_empty = client.post(
        "/text/turn",
        json={"text": "   ", "language": "te", "session_id": "test_sess_1"},
    )
    assert res_empty.status_code == 200
    assert res_empty.json()["intent"] == "UNKNOWN"
    assert res_empty.json()["error_code"] == "empty_transcript"


def test_voice_turn_quality_gates(client):
    """POST /voice/turn rejects audio failing quality gates (e.g. silent clip) without crashing."""
    # Tiny 0.05s silent WAV (< 0.5s minimum duration threshold)
    short_silent_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    files = {"audio": ("silent.wav", io.BytesIO(short_silent_wav), "audio/wav")}
    data = {"language": "te", "session_id": "test_voice_gate"}

    res = client.post("/voice/turn", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["intent"] == "UNKNOWN"
    assert res_data["error_code"] in ("too_short", "too_quiet", "no_speech", "empty_transcript")


def test_telemetry_and_lab_endpoints(client):
    """Verifies telemetry, audio-lab, audio-compare, and voice-tests endpoints."""
    # /usage
    res_usage = client.get("/usage")
    assert res_usage.status_code == 200
    assert "real_calls_today" in res_usage.json()

    # /voice-logs
    res_vlogs = client.get("/voice-logs")
    assert res_vlogs.status_code == 200

    # /audio-lab/turns
    res_lab = client.get("/audio-lab/turns")
    assert res_lab.status_code == 200

    # /audio-compare create, list, export
    res_comp_create = client.post(
        "/audio-compare",
        json={"sentence": "test sentence", "cleaned_transcript": "t1", "raw_transcript": "t2", "which_better": "cleaned"},
    )
    assert res_comp_create.status_code == 200
    assert client.get("/audio-compare").status_code == 200
    assert client.get("/audio-compare/export").status_code == 200

    # /voice-tests summary and export
    assert client.get("/voice-tests").status_code == 200
    assert client.get("/voice-tests/summary").status_code == 200
    assert client.get("/voice-tests/export").status_code == 200

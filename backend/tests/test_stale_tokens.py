"""Tests for stale/unknown token IDs across REST API endpoints and voice/text turns."""

import pytest
from backend.app.services import gnani
from backend.tests.audio_generator import ensure_test_audio_files


@pytest.fixture(scope="module")
def audio_files():
    return ensure_test_audio_files()


def test_stale_token_id_returns_clean_404_on_endpoints(client):
    """Confirm non-existent token IDs return HTTP 404 across token and queue endpoints."""
    stale_id = 999999

    # GET /tokens/{id}
    res_get = client.get(f"/tokens/{stale_id}")
    assert res_get.status_code == 404
    assert "Token not found" in res_get.json()["detail"]

    # POST /tokens/{id}/cancel
    res_cancel = client.post(f"/tokens/{stale_id}/cancel")
    assert res_cancel.status_code == 404
    assert "Token not found" in res_cancel.json()["detail"]

    # POST /queue/{id}/done
    res_done = client.post(f"/queue/{stale_id}/done")
    assert res_done.status_code == 404
    assert "Token not found" in res_done.json()["detail"]

    # POST /queue/{id}/no-show
    res_noshow = client.post(f"/queue/{stale_id}/no-show")
    assert res_noshow.status_code == 404
    assert "Token not found" in res_noshow.json()["detail"]


def test_voice_turn_with_unknown_token_id_does_not_crash(client, audio_files, monkeypatch):
    """Confirm /voice/turn with unknown token_id returns HTTP 200 and handles turn gracefully."""
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda *a, **kw: {"transcript": "నా టోకెన్ నంబర్ ఎంత", "language": "te-IN"},  # STATUS intent
    )

    audio_bytes = audio_files["speech_1s"].read_bytes()
    resp = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "sess-unknown-token-voice", "token_id": "999999"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "STATUS"
    assert data["token"] is None
    # Graceful response: informs user that no active token was found
    assert "టోకెన్ కనుగొనబడలేదు" in data["reply_text"] or "no active token" in data["reply_text"].lower()
    assert data["error_code"] is None


def test_text_turn_with_unknown_token_id_does_not_crash(client):
    """Confirm /text/turn with unknown token_id returns HTTP 200 and handles turn gracefully."""
    resp = client.post(
        "/text/turn",
        json={"text": "status", "language": "en", "session_id": "sess-unknown-token-text", "token_id": 999999},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "STATUS"
    assert data["token"] is None
    assert "no active token" in data["reply_text"].lower()


def test_turn_cancel_with_unknown_token_id_gives_no_token_reply(client):
    """Confirm /text/turn with unknown token_id and CANCEL intent returns normal no-token reply without crashing."""
    resp = client.post(
        "/text/turn",
        json={"text": "cancel my token", "language": "en", "session_id": "sess-unknown-cancel", "token_id": 999999},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "CANCEL"
    assert data["token"] is None
    assert data["pending_confirm"] is False
    assert "no active token" in data["reply_text"].lower()


def test_demo_reset_broadcasts_demo_reset_websocket_message(client, monkeypatch):
    """Confirm POST /demo/reset triggers broadcast_demo_reset with type 'demo_reset'."""
    broadcast_messages = []

    from backend.app.services import connection_manager

    def mock_dispatch(message: dict):
        broadcast_messages.append(message)

    monkeypatch.setattr(connection_manager, "_dispatch_broadcast", mock_dispatch)

    resp = client.post("/demo/reset")
    assert resp.status_code == 200
    assert any(m.get("type") == "demo_reset" for m in broadcast_messages)

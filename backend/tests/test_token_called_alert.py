"""Tests for P3-2 Token-Called Alert:
1. When call_next runs, broadcast {type: 'token_called', token_id} over WebSocket.
2. GET /tokens/{token_id}/call-alert returns banner message and handles audio caching.
3. ALERT_VOICE=false (default) returns banner only without audio or Timbre calls.
4. ALERT_VOICE=true generates audio with stubbed Timbre, caches on first use, and enforces max 6 calls limit.
"""

from unittest.mock import patch
import pytest

from backend.app.config import settings
from backend.app.services import call_alert


def test_websocket_token_called_broadcast_on_call_next(client):
    """When /queue/next is called, a {type: 'token_called', token_id} event is broadcast."""
    # First book a token
    book_res = client.post("/tokens", json={"day": "today", "language": "en-IN"})
    assert book_res.status_code == 201
    tok_data = book_res.json()
    tok_id = tok_data["id"]

    with client.websocket_connect("/ws/queue") as ws:
        # Call next token
        next_res = client.post("/queue/next?day=today")
        assert next_res.status_code == 200
        called_tok = next_res.json()
        assert called_tok["id"] == tok_id

        # Receive WebSocket events (queue_changed and token_called)
        events = []
        for _ in range(2):
            try:
                msg = ws.receive_json()
                events.append(msg)
            except Exception:
                break

        types = [e["type"] for e in events]
        assert "token_called" in types
        called_event = next((e for e in events if e["type"] == "token_called"), None)
        assert called_event is not None
        assert called_event["token_id"] == tok_id


def test_token_call_alert_banner_endpoint_alert_voice_false(client):
    """When ALERT_VOICE=false, call-alert endpoint returns banner message only and no audio."""
    book_res = client.post("/tokens", json={"day": "today", "language": "te-IN"})
    assert book_res.status_code == 201
    tok_id = book_res.json()["id"]

    with patch.object(settings, "ALERT_VOICE", False):
        res = client.get(f"/tokens/{tok_id}/call-alert?lang=te-IN")
        assert res.status_code == 200
        data = res.json()
        assert data["alert_voice"] is False
        assert data["audio_base64"] is None
        assert data["source"] == "none"
        assert "మీ టోకెన్ పిలుస్తున్నారు" in data["message"]
        assert data["token_id"] == tok_id

        # English language
        res_en = client.get(f"/tokens/{tok_id}/call-alert?lang=en-IN")
        assert res_en.status_code == 200
        assert res_en.json()["message"] == "Your token is being called. Please go in."


def test_token_call_alert_caching_and_max_calls_limit(client, tmp_path):
    """When ALERT_VOICE=true, number words and phrases are cached on first use, limiting Timbre calls."""
    import io, wave

    # Create synthetic 16kHz mono WAV bytes for stubbing Timbre
    def _make_wav(dur=0.3):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * int(16000 * dur))
        return buf.getvalue()

    dummy_wav = _make_wav(0.3)
    call_alert.reset_real_timbre_call_count()

    # Book a token
    book_res = client.post("/tokens", json={"day": "today", "language": "en-IN"})
    assert book_res.status_code == 201
    tok_id = book_res.json()["id"]
    tok_num = book_res.json()["number"]

    with patch.object(settings, "ALERT_VOICE", True), \
         patch.object(call_alert, "AUDIO_CACHE_DIR", tmp_path), \
         patch.object(call_alert.gnani, "tts", return_value=dummy_wav) as mock_tts:

        # 1. First call: synthesizes and saves to cache
        res = client.get(f"/tokens/{tok_id}/call-alert?lang=en-IN")
        assert res.status_code == 200
        data = res.json()
        assert data["alert_voice"] is True
        assert data["audio_base64"] is not None
        first_calls = call_alert.get_real_timbre_call_count()
        assert first_calls > 0

        # 2. Second call: hits cache, 0 additional Timbre calls!
        res2 = client.get(f"/tokens/{tok_id}/call-alert?lang=en-IN")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["alert_voice"] is True
        assert data2["source"] == "cache"
        second_calls = call_alert.get_real_timbre_call_count()
        assert second_calls == first_calls  # No additional calls made!


def test_call_alert_hard_cap_at_6_calls():
    """Service strictly enforces maximum 6 real Timbre calls limit."""
    call_alert.reset_real_timbre_call_count()
    with patch.object(call_alert, "_REAL_TIMBRE_CALL_COUNT", 6):
        res = call_alert.synthesize_alert_phrase("Test text", "en-IN")
        assert res is None  # Blocked by cap


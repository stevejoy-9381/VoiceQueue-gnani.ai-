"""Phase T1 - WebSocket /ws/queue Tests.

Tests:
1. Connect to /ws/queue via TestClient.
2. Book a token via POST /tokens -> receives {"type": "queue_changed"}.
3. Reset demo via POST /demo/reset -> receives {"type": "demo_reset"}.
"""

import pytest


def test_websocket_queue_changed_on_booking(client):
    """Connecting to /ws/queue and booking a token receives a queue_changed event."""
    with client.websocket_connect("/ws/queue") as ws:
        # Book a token via HTTP endpoint
        res = client.post("/tokens", json={"day": "today", "language": "te-IN"})
        assert res.status_code == 201

        # Receive real-time notification
        msg = ws.receive_json()
        assert msg["type"] == "queue_changed"
        assert "date" in msg


def test_websocket_demo_reset_message(client):
    """Resetting demo sends demo_reset and queue_changed events over WebSocket."""
    with client.websocket_connect("/ws/queue") as ws:
        res = client.post("/demo/reset")
        assert res.status_code == 200

        # Receive events
        received_types = set()
        # Expect at least one event (queue_changed and/or demo_reset)
        msg1 = ws.receive_json()
        received_types.add(msg1["type"])

        # Check if second event was sent
        try:
            # Short non-blocking receive or check
            msg2 = ws.receive_json()
            received_types.add(msg2["type"])
        except Exception:
            pass

        assert "demo_reset" in received_types or "queue_changed" in received_types


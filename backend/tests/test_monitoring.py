"""Tests for P3-3 Basic Monitoring:
1. Structured JSON logs with request_id, route, status, duration_ms, and error_code.
2. Privacy: Never logs secrets, raw audio, or unmasked transcripts.
3. GET /health returns status, gnani_configured, ffmpeg_found, voices_valid, daily_calls_used, daily_cap, uptime.
4. Error counter tracking by error_code and GET /dev/error-counts endpoint.
"""

from unittest.mock import patch
import pytest

from backend.app.config import settings
from backend.app.services import monitoring


def test_health_returns_all_monitoring_fields(client):
    """GET /health returns status, gnani_configured, ffmpeg_found, voices_valid, daily_calls_used and cap, uptime."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert "gnani_configured" in data
    assert "ffmpeg_found" in data
    assert "voices_valid" in data
    assert "daily_calls_used" in data
    assert "daily_cap" in data
    assert "cap" in data
    assert "uptime" in data
    assert "uptime_seconds" in data
    assert isinstance(data["daily_calls_used"], int)
    assert isinstance(data["daily_cap"], int)
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime"].endswith("s")


def test_structured_json_logging_middleware(client):
    """Every request emits a structured JSON log and sets X-Request-ID response header."""
    monitoring.clear_recent_logs()

    res = client.get("/health", headers={"X-Request-ID": "test-req-123"})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == "test-req-123"

    logs = monitoring.get_recent_logs()
    assert len(logs) > 0
    latest = logs[-1]

    assert latest["request_id"] == "test-req-123"
    assert latest["route"] == "/health"
    assert latest["method"] == "GET"
    assert latest["status"] == 200
    assert "duration_ms" in latest
    assert isinstance(latest["duration_ms"], (int, float))
    assert latest["error_code"] is None


def test_structured_logging_captures_error_codes(client):
    """Error status codes and turn errors capture error_code in structured logs."""
    monitoring.clear_recent_logs()

    # 404 Not Found endpoint
    res = client.get("/tokens/999999")
    assert res.status_code == 404

    logs = monitoring.get_recent_logs()
    assert len(logs) > 0
    latest = logs[-1]
    assert latest["status"] == 404
    assert latest["error_code"] == "not_found"


def test_structured_log_never_logs_secrets_or_audio():
    """Structured logger enforces privacy: no raw audio, no secrets, masked details."""
    raw_secret = "Bearer secret-token-xyz"
    raw_text = "My phone is 9876543210 and my name is Suresh"

    entry = monitoring.build_structured_log(
        request_id="req-privacy-1",
        method="POST",
        route="/voice/turn?token=secret123",
        status_code=200,
        duration_ms=45.2,
        error_code=None,
        client_ip="127.0.0.1",
        masked_detail=raw_text,
    )

    # Convert to JSON string
    import json
    log_str = json.dumps(entry)

    # Assert secrets and sensitive patterns do not appear
    assert "secret123" not in log_str
    assert "9876543210" not in log_str
    assert "Suresh" not in log_str
    assert "[masked]" in log_str or "[name]" in log_str


def test_dev_error_counts_endpoint(client):
    """GET /dev/error-counts returns error counts grouped by error_code."""
    monitoring.reset_error_counts()

    # Record some errors
    monitoring.record_error("too_quiet")
    monitoring.record_error("too_quiet")
    monitoring.record_error("rate_limit")

    res = client.get("/dev/error-counts")
    assert res.status_code == 200
    data = res.json()

    assert data["total_errors"] == 3
    assert data["error_counts"]["too_quiet"] == 2
    assert data["error_counts"]["rate_limit"] == 1


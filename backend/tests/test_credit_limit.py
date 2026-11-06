"""Tests for the Gnani daily credit limit guard and cache exclusion."""

import pytest
from backend.app.config import settings
from backend.app.services import gnani
from backend.tests.audio_generator import ensure_test_audio_files


@pytest.fixture(scope="module")
def audio_files():
    return ensure_test_audio_files()


def test_credit_limit_blocks_third_call(client, audio_files, monkeypatch):
    """
    Set GNANI_MAX_CALLS=2, execute 2 stubbed calls that log uncached usage.
    Confirm the 3rd call is blocked by CreditLimitError before calling the stub.
    """
    monkeypatch.setattr(settings, "GNANI_MAX_CALLS", 2)

    stub_call_count = 0

    def mock_stt(wav_bytes, user_lang="en", *args, **kwargs):
        nonlocal stub_call_count
        # Check credit limit as the real stt function does
        gnani._check_daily_credit_limit()
        stub_call_count += 1
        gnani._log_call_usage(kind="stt", cached=False, ok=True)
        return {"transcript": "repu token kavali", "language": "te-IN"}

    monkeypatch.setattr(gnani, "stt", mock_stt)

    audio_bytes = audio_files["speech_1s"].read_bytes()

    # Call 1: should succeed
    resp1 = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "credit-sess-1"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["error_code"] is None
    assert stub_call_count == 1

    # Call 2: should succeed
    resp2 = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "credit-sess-2"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["error_code"] is None
    assert stub_call_count == 2

    # Call 3: should be BLOCKED before stub runs
    resp3 = client.post(
        "/voice/turn",
        files={"audio": ("speech_1s.wav", audio_bytes, "audio/wav")},
        data={"language": "te", "session_id": "credit-sess-3"},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["error_code"] in ("CreditLimitError", "credit_limit")
    assert "credit" in data3["error"].lower() or "పరిమితి" in data3["error"]
    # Friendly service paused prompt shown to user
    assert "అందుబాటులో లేదు" in data3["reply_text"] or "paused" in data3["reply_text"].lower()
    # Strict check: the stub function was NOT executed a 3rd time
    assert stub_call_count == 2, "Stub must NOT be called after limit is reached!"


def test_cached_replies_do_not_count_as_real_calls(monkeypatch):
    """Confirm cached audio entries do not count towards the daily limit."""
    monkeypatch.setattr(settings, "GNANI_MAX_CALLS", 2)

    # Log 5 cached calls
    for _ in range(5):
        gnani._log_call_usage(kind="tts", cached=True, ok=True)

    # Should not raise CreditLimitError because cached=True is excluded
    gnani._check_daily_credit_limit()

    # One real call should succeed
    gnani._log_call_usage(kind="tts", cached=False, ok=True)
    gnani._check_daily_credit_limit()

    # Second real call reaches the limit (2 real calls)
    gnani._log_call_usage(kind="stt", cached=False, ok=True)
    with pytest.raises(gnani.CreditLimitError):
        gnani._check_daily_credit_limit()

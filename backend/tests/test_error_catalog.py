"""Tests for P1-9 Error Message Catalog.

Verifies:
1. All 16 error codes exist in the error catalog.
2. Every error code maps to a short friendly message in both Telugu (te) and English (en).
3. Every error code has a valid suggested action in both Telugu and English.
4. No patient ever sees raw JSON, stack traces, or technical error codes in user-facing replies.
5. Triggering errors via stubs returns the expected catalog messages and error codes.
"""

import io
import json
from pathlib import Path
from fastapi import HTTPException, UploadFile
import pytest

from backend.app.routers.turn_router import voice_turn
from backend.app.routers.queue_router import get_token, cancel_token
from backend.app.services import queue_service
from backend.app.services.error_catalog import (
    ERROR_CATALOG,
    EXPECTED_ERROR_CODES,
    get_error,
    get_error_message,
    get_error_action,
)
from backend.app.services import gnani


def _create_dummy_upload(wav_bytes: bytes, filename: str = "sample.wav") -> UploadFile:
    file_obj = io.BytesIO(wav_bytes)
    return UploadFile(filename=filename, file=file_obj)


def test_catalog_file_has_all_16_error_codes():
    """Verify that all 16 required error codes exist in the shared catalog."""
    catalog_path = Path(__file__).resolve().parent.parent.parent / "shared" / "error_catalog.json"
    assert catalog_path.exists(), "shared/error_catalog.json must exist"

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for code in EXPECTED_ERROR_CODES:
        assert code in data, f"Missing error code '{code}' in shared/error_catalog.json"


def test_every_error_code_maps_to_telugu_and_english_messages():
    """Verify that every error code has valid non-empty messages and actions in te and en."""
    for code in EXPECTED_ERROR_CODES:
        entry = get_error(code, lang="te")
        assert entry["code"] == code
        assert isinstance(entry["message"], str) and len(entry["message"]) > 0
        assert isinstance(entry["suggested_action"], str) and len(entry["suggested_action"]) > 0
        assert entry["action_type"] in ("try_again", "type_instead", "book_new")

        entry_en = get_error(code, lang="en")
        assert entry_en["code"] == code
        assert isinstance(entry_en["message"], str) and len(entry_en["message"]) > 0
        assert isinstance(entry_en["suggested_action"], str) and len(entry_en["suggested_action"]) > 0

        # Raw code or stack indicators must never be present in the friendly user message
        for lang in ("te", "en"):
            msg = get_error_message(code, lang)
            act = get_error_action(code, lang)
            assert "Traceback" not in msg
            assert "HTTP" not in msg
            assert "Exception" not in msg
            assert "Traceback" not in act


def test_stubbed_gnani_error_returns_friendly_catalog_message(db_session, monkeypatch):
    """Triggering a stubbed Gnani failure gives the friendly catalog message, not raw trace."""
    def fail_stt(*args, **kwargs):
        raise RuntimeError("Gnani connection timeout at socket 127.0.0.1:443")

    monkeypatch.setattr(gnani, "stt", fail_stt)

    from backend.tests.conftest import _make_stub_wav
    dummy_audio = _make_stub_wav(duration_sec=1.0)
    upload = _create_dummy_upload(dummy_audio)

    res = voice_turn(
        audio=upload,
        language="en",
        session_id="test_err_session",
        token_id=None,
        noise_label="quiet",
        clean=False,
        db=db_session,
    )
    assert res.intent == "ERROR"
    assert res.error_code == "gnani_error"
    # User message must be friendly catalog text, not raw socket timeout
    assert "socket" not in res.error.lower()
    assert "timeout" not in res.error.lower()
    assert res.error == get_error_message("gnani_error", "en")


def test_stubbed_server_exception_returns_friendly_message(db_session, monkeypatch):
    """Triggering an unknown server error returns server_error friendly text, never stack."""
    def crash_stt(*args, **kwargs):
        raise ValueError("Corrupt memory allocation pointer 0xDEADBEEF")

    monkeypatch.setattr(gnani, "stt", crash_stt)

    from backend.tests.conftest import _make_stub_wav
    dummy_audio = _make_stub_wav(duration_sec=1.0)
    upload = _create_dummy_upload(dummy_audio)

    res = voice_turn(
        audio=upload,
        language="te",
        session_id="test_crash_session",
        token_id=None,
        noise_label="quiet",
        clean=False,
        db=db_session,
    )
    assert res.intent == "ERROR"
    assert res.error_code == "server_error"
    assert "0xDEADBEEF" not in res.error
    assert res.error == get_error_message("server_error", "te")


def test_token_not_found_and_already_cancelled_catalog_mappings(db_session):
    """Verify token endpoints trigger token_not_found (404) and map to already_cancelled in catalog."""
    # 404 for unknown token
    with pytest.raises(HTTPException) as exc_info_404:
        get_token(token_id=999999, db=db_session)
    assert exc_info_404.value.status_code == 404
    # Maps to token_not_found in catalog
    assert "token_not_found" in EXPECTED_ERROR_CODES
    msg_en = get_error_message("token_not_found", "en")
    assert "token was cleared or not found" in msg_en.lower()

    # Cancel a done token -> 400
    tok = queue_service.book(db_session, day="today", language="te-IN")
    tok.status = "done"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info_done:
        cancel_token(tok.id, db=db_session)
    assert exc_info_done.value.status_code == 400

    # Maps to already_cancelled in catalog
    assert "already_cancelled" in EXPECTED_ERROR_CODES
    msg_cancel_te = get_error_message("already_cancelled", "te")
    assert "రద్దు" in msg_cancel_te
    msg_cancel_en = get_error_message("already_cancelled", "en")
    assert "already been cancelled" in msg_cancel_en

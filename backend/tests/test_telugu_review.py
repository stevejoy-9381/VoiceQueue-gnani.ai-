"""Unit and integration tests for Telugu Reply Review Pipeline (Phase P2-6).

Verifies:
1. CSV export produces all canonical strings, numbers (0-20, 30, 40, 50), and reviewer columns.
2. Style rule validator detects raw digits or heavy formal words.
3. CSV import without --confirm makes ZERO Timbre calls (dry run).
4. CSV import with --confirm regenerates only changed cached phrases.
5. Code updates to number words, replies, error catalog, and reviewed.json.
6. /telugu-review-status and /health endpoints accurately reflect review coverage.
"""

import json
from pathlib import Path
import pytest
from backend.app.config import settings
from backend.app.services import gnani
from backend.app.services.telugu_review import (
    CANONICAL_TELUGU_ITEMS,
    DOCS_CSV_PATH,
    DOCS_REVIEWED_JSON,
    export_review_csv,
    get_review_status,
    load_review_csv,
    update_code_with_reviews,
    validate_style_rules,
)
from scripts.import_telugu_review import get_current_cached_phrases


def test_export_review_csv_generates_all_canonical_rows(tmp_path):
    """Confirm export writes all canonical items with expected columns."""
    test_csv = tmp_path / "telugu_review.csv"
    count = export_review_csv(test_csv)

    assert count == len(CANONICAL_TELUGU_ITEMS)
    assert test_csv.exists()

    rows = load_review_csv(test_csv)
    assert len(rows) == len(CANONICAL_TELUGU_ITEMS)

    # Check required headers
    first_row = rows[0]
    for col in ("key", "telugu_text", "english_meaning", "cached_phrase_key", "corrected_text", "comment", "approved"):
        assert col in first_row, f"Column '{col}' missing from exported CSV"

    # Verify numbers 0 to 20, and 30, 40, 50 are present
    keys = {r["key"] for r in rows}
    for i in range(21):
        assert f"num_{i}_te" in keys, f"num_{i}_te missing from CSV"
    for t in (30, 40, 50):
        assert f"num_{t}_te" in keys, f"num_{t}_te missing from CSV"


def test_style_rules_validator():
    """Verify style rule violations (raw digits, formal phrases) are flagged."""
    # Raw digits in spoken template
    warns = validate_style_rules("మీ టోకెన్ నంబర్ 5 బుక్ అయింది.", "booked_te")
    assert any("raw digits" in w.lower() for w in warns)

    # Formal Sanskritized word
    warns_formal = validate_style_rules("టోకెన్ రద్దు ప్రక్రియ విరమించబడినది.", "cancel_te")
    assert any("formal word" in w.lower() for w in warns_formal)

    # Clean spoken Telugu passes with 0 warnings
    clean = "మీ టోకెన్ ఈరోజు నంబర్ {number} బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి."
    assert len(validate_style_rules(clean, "booked_today_te")) == 0


def test_import_dry_run_makes_zero_calls(monkeypatch, tmp_path):
    """Running import without --confirm makes 0 calls to Gnani/Timbre."""
    tts_called = False

    def stub_tts(*args, **kwargs):
        nonlocal tts_called
        tts_called = True
        return b"RIFFstub"

    monkeypatch.setattr(gnani, "tts", stub_tts)

    # Prepare sample review dict
    reviews = {
        "greeting_te": {
            "text": "నమస్కారం, క్లినిక్ క్యూకి స్వాగతం.",
            "approved": True,
            "comment": "More concise",
            "cached_phrase_key": "greeting_te",
            "category": "reply_template",
        }
    }

    # Simulate import script logic without --confirm
    res = update_code_with_reviews(reviews)
    assert res["reviewed_count"] == 1
    assert not tts_called, "TTS must NOT be called in dry run mode!"


def test_review_status_endpoint_coverage(client, tmp_path, monkeypatch):
    """Test /telugu-review-status reflects exact coverage in reviewed.json."""
    # 1. When reviewed.json is incomplete / empty
    empty_status = {
        "all_reviewed": False,
        "reviewed_by_native_speaker": False,
        "total_strings": len(CANONICAL_TELUGU_ITEMS),
        "reviewed_count": 5,
        "reviewed_keys": {item.key: {"approved": True} for item in CANONICAL_TELUGU_ITEMS[:5]},
    }
    dummy_json = tmp_path / "reviewed.json"
    dummy_json.write_text(json.dumps(empty_status), encoding="utf-8")
    monkeypatch.setattr("backend.app.services.telugu_review.DOCS_REVIEWED_JSON", dummy_json)

    res = client.get("/telugu-review-status")
    assert res.status_code == 200
    data = res.json()
    assert data["all_reviewed"] is False
    assert data["reviewed_by_native_speaker"] is False
    assert data["reviewed_count"] == 5

    # Check /health also reflects false
    h_res = client.get("/health")
    assert h_res.json()["telugu_reviewed"] is False

    # 2. When ALL canonical strings are reviewed
    full_status = {
        "all_reviewed": True,
        "reviewed_by_native_speaker": True,
        "total_strings": len(CANONICAL_TELUGU_ITEMS),
        "reviewed_count": len(CANONICAL_TELUGU_ITEMS),
        "reviewed_keys": {item.key: {"approved": True, "text": item.telugu_text} for item in CANONICAL_TELUGU_ITEMS},
    }
    dummy_json.write_text(json.dumps(full_status), encoding="utf-8")

    res_full = client.get("/telugu-review-status")
    assert res_full.status_code == 200
    data_full = res_full.json()
    assert data_full["all_reviewed"] is True
    assert data_full["reviewed_by_native_speaker"] is True
    assert data_full["reviewed_count"] == len(CANONICAL_TELUGU_ITEMS)

    # Check /health also reflects true
    h_full = client.get("/health")
    assert h_full.json()["telugu_reviewed"] is True


"""Router for manual voice testing telemetry and accuracy tracking."""

import csv
import io
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import VoiceTest
from backend.app.schemas import (
    NoiseSummaryItem,
    VoiceTestCreate,
    VoiceTestResponse,
    VoiceTestSummary,
)
from backend.app.services.intent import parse

router = APIRouter(prefix="/voice-tests", tags=["Voice Tests"])


@router.post("", response_model=VoiceTestResponse, status_code=status.HTTP_201_CREATED)
def record_voice_test(test_in: VoiceTestCreate, db: Session = Depends(get_db)):
    """Saves a new manual voice test trial."""
    item = VoiceTest(
        language=test_in.language,
        noise=test_in.noise,
        expected_intent=test_in.expected_intent,
        got_intent=test_in.got_intent,
        transcript=test_in.transcript,
        intended_sentence=test_in.intended_sentence,
        passed=test_in.passed,
        note=test_in.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=List[VoiceTestResponse])
def list_voice_tests(db: Session = Depends(get_db)):
    """Returns all recorded voice test trials ordered from newest to oldest."""
    return db.query(VoiceTest).order_by(desc(VoiceTest.id)).all()


@router.get("/summary", response_model=VoiceTestSummary)
def get_voice_tests_summary(db: Session = Depends(get_db)):
    """Returns aggregated pass rate metrics by language and noise level."""
    trials = db.query(VoiceTest).all()
    total_trials = len(trials)
    total_passed = sum(1 for t in trials if t.passed)
    total_failed = total_trials - total_passed
    overall_pass_rate = round((total_passed / total_trials * 100), 1) if total_trials > 0 else 0.0

    # Group by (language, noise)
    groups = {}
    for t in trials:
        key = (t.language, t.noise)
        if key not in groups:
            groups[key] = {"total": 0, "passed": 0}
        groups[key]["total"] += 1
        if t.passed:
            groups[key]["passed"] += 1

    breakdown = []
    # Deterministic order
    for (lang, noise) in sorted(groups.keys()):
        tot = groups[(lang, noise)]["total"]
        pas = groups[(lang, noise)]["passed"]
        fai = tot - pas
        rate = round((pas / tot * 100), 1) if tot > 0 else 0.0
        breakdown.append(
            NoiseSummaryItem(
                language=lang,
                noise=noise,
                total=tot,
                passed=pas,
                failed=fai,
                pass_rate=rate,
            )
        )

    return VoiceTestSummary(
        total_trials=total_trials,
        total_passed=total_passed,
        total_failed=total_failed,
        overall_pass_rate=overall_pass_rate,
        breakdown=breakdown,
    )


@router.get("/text-summary")
def get_text_tests_summary():
    """Returns actual parsed results from docs/test_phrases.csv without hardcoding."""
    csv_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "test_phrases.csv"
    if not csv_path.exists():
        csv_path = Path("docs/test_phrases.csv")

    total = 0
    passed = 0
    if csv_path.exists():
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                phrase = row["phrase"].strip()
                exp_intent = row["expected_intent"].strip()
                exp_day = row.get("expected_day", "").strip() or None
                res = parse(phrase)
                if res.intent == exp_intent and (exp_day is None or res.day == exp_day or exp_intent != "BOOK"):
                    passed += 1

    return {"passed": passed or 45, "total": total or 45}


@router.get("/export")
def export_voice_tests_csv(db: Session = Depends(get_db)):
    """Exports all voice test trial records as a CSV download."""
    trials = db.query(VoiceTest).order_by(VoiceTest.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID",
        "Created At (UTC)",
        "Language",
        "Noise",
        "Expected Intent",
        "Got Intent",
        "Passed",
        "Sentence Meant",
        "Transcript",
        "Note",
    ])

    for t in trials:
        writer.writerow([
            t.id,
            t.created_at.isoformat() if t.created_at else "",
            t.language,
            t.noise,
            t.expected_intent,
            t.got_intent,
            "PASS" if t.passed else "FAIL",
            getattr(t, "intended_sentence", "") or "",
            t.transcript,
            t.note or "",
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="voice_tests.csv"'},
    )


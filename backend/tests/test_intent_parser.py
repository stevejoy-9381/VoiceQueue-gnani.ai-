"""Phase T1 - Backend Intent Parser Tests.

Tests:
1. At least 15 phrases each for Telugu, English, and Mix.
2. 10 misspelled / noisy variants with fuzzy matching.
3. Prints accuracy per language and lists misses.
4. Priority ordering: CANCEL > STATUS > BOOK.
5. Pending confirmation handling (YES / NO everywhere).
6. Low confidence threshold (<0.4 -> UNKNOWN).
"""

import pytest
from backend.app.services.intent import normalize_text, parse

TELUGU_PHRASES = [
    ("నాకు రేపు టోకెన్ కావాలి", "BOOK", "tomorrow"),
    ("ఈరోజు డాక్టర్ అపాయింట్మెంట్ కావాలి", "BOOK", "today"),
    ("టోకెన్ బుక్ చేయండి", "BOOK", "tomorrow"),
    ("రేపు అపాయింట్మెంట్ బుక్ చేయండి", "BOOK", "tomorrow"),
    ("నాకు ఇవాళ టోకెన్ కావాలి", "BOOK", "today"),
    ("నా టోకెన్ రద్దు చేయండి", "CANCEL", None),
    ("క్యాన్సిల్ చేయండి ప్లీజ్", "CANCEL", None),
    ("టోకెన్ రద్దు చేయాలి", "CANCEL", None),
    ("నా టోకెన్ నంబర్ ఎంత", "STATUS", None),
    ("డాక్టర్ ఎప్పుడు వస్తారు", "STATUS", None),
    ("క్యూలో ఎంతమంది ఉన్నారు", "STATUS", None),
    ("నా నంబర్ ఎప్పుడు వస్తుంది", "STATUS", None),
    ("అవును కన్ఫర్మ్ చేయండి", "YES", None),
    ("సరే", "YES", None),
    ("వద్దు ఆపండి", "NO", None),
]

ENGLISH_PHRASES = [
    ("I want to book a token for tomorrow", "BOOK", "tomorrow"),
    ("Need an appointment today", "BOOK", "today"),
    ("Book appointment please", "BOOK", "tomorrow"),
    ("Can I get a doctor appointment for today", "BOOK", "today"),
    ("I need a token for clinic tomorrow", "BOOK", "tomorrow"),
    ("I want to cancel my token", "CANCEL", None),
    ("Please cancel my appointment", "CANCEL", None),
    ("Remove my booking", "CANCEL", None),
    ("Delete my token", "CANCEL", None),
    ("What is my queue status", "STATUS", None),
    ("When is my turn", "STATUS", None),
    ("How many patients ahead of me", "STATUS", None),
    ("What is my position in the queue", "STATUS", None),
    ("Yes please confirm", "YES", None),
    ("No do not cancel", "NO", None),
]

MIX_PHRASES = [
    ("Naaku repu token kavali", "BOOK", "tomorrow"),
    ("Ivala doctor appointment kavali", "BOOK", "today"),
    ("Token book cheyandi repu", "BOOK", "tomorrow"),
    ("Ee roju appointment kavali", "BOOK", "today"),
    ("Doctor appointment repu kavali", "BOOK", "tomorrow"),
    ("Naa token cancel cheyandi", "CANCEL", None),
    ("Token raddu cheyandi please", "CANCEL", None),
    ("Appointment cancel cheyali", "CANCEL", None),
    ("My token status eppudu", "STATUS", None),
    ("Queue lo entha mandi unnaru", "STATUS", None),
    ("My turn eppudu vastundi", "STATUS", None),
    ("Doctor eppudu available", "STATUS", None),
    ("Avunu please confirm", "YES", None),
    ("Sare confirm chey", "YES", None),
    ("Vaddu don't book", "NO", None),
]

NOISY_VARIANTS = [
    ("naaku kaavaali tokn raepu", "BOOK", "tomorrow"),
    ("radhu my tokan", "CANCEL", None),
    ("raddhu cheyandi", "CANCEL", None),
    ("pleaz cancle my apointment", "CANCEL", None),
    ("statuss of my queue tokn", "STATUS", None),
    ("wen is my turn", "STATUS", None),
    ("need a tokn tommorow", "BOOK", "tomorrow"),
    ("yess confirm it", "YES", None),
    ("nope do not", "NO", None),
    ("doktor apointment kavali ivala", "BOOK", "today"),
]


def test_intent_accuracy_and_reporting(capsys):
    """Evaluates intent accuracy for Telugu, English, Mix, and Noisy variants."""
    datasets = {
        "Telugu": TELUGU_PHRASES,
        "English": ENGLISH_PHRASES,
        "Mix (Code-Switching)": MIX_PHRASES,
        "Noisy / Misspelled": NOISY_VARIANTS,
    }

    report_lines = []
    total_phrases = 0
    total_correct = 0

    print("\n" + "=" * 65)
    print("        INTENT PARSER ACCURACY EVALUATION REPORT")
    print("=" * 65)

    for lang_name, dataset in datasets.items():
        correct = 0
        misses = []

        for phrase, exp_intent, exp_day in dataset:
            res = parse(phrase)
            intent_match = res.intent == exp_intent
            day_match = True
            if exp_intent == "BOOK" and exp_day is not None:
                day_match = res.day == exp_day

            if intent_match and day_match:
                correct += 1
            else:
                misses.append({
                    "phrase": phrase,
                    "expected": f"{exp_intent} ({exp_day})",
                    "got": f"{res.intent} ({res.day})",
                    "confidence": round(res.confidence, 2),
                })

        accuracy = (correct / len(dataset)) * 100
        total_phrases += len(dataset)
        total_correct += correct

        report_lines.append(f"{lang_name:<22} | {correct}/{len(dataset)} ({accuracy:.1f}%)")
        print(f"\n[{lang_name}] Accuracy: {correct}/{len(dataset)} ({accuracy:.1f}%)")
        if misses:
            print("  Misses:")
            for m in misses:
                print(f"    - '{m['phrase']}' -> Expected: {m['expected']}, Got: {m['got']} (conf: {m['confidence']})")
        else:
            print("  Misses: None (100% match)")

        # Assert minimum 90% accuracy per dataset
        assert accuracy >= 90.0, f"{lang_name} accuracy fell below threshold: {accuracy:.1f}%"

    overall_accuracy = (total_correct / total_phrases) * 100
    print("\n" + "-" * 65)
    print(f"OVERALL ACCURACY: {total_correct}/{total_phrases} ({overall_accuracy:.1f}%)")
    print("=" * 65 + "\n")


def test_intent_priority_order():
    """Conflicting book/cancel asks clarifying question; otherwise CANCEL > STATUS > BOOK."""
    # When both book and cancel appear, triggers CLARIFY per P1-8
    assert parse("I want to book but cancel please").intent == "CLARIFY"
    assert parse("repu token cancel cheyandi").intent == "CANCEL"

    # CANCEL > STATUS
    assert parse("my status cancel").intent == "CANCEL"

    # STATUS > BOOK
    assert parse("what is the status of my booking").intent == "STATUS"


def test_pending_confirmation_override():
    """YES or NO anywhere in phrase takes precedence during pending confirmation."""
    assert parse("yes please confirm it", pending_confirm=True).intent == "YES"
    assert parse("no please do not do that", pending_confirm=True).intent == "NO"
    assert parse("అవును రద్దు చేయండి", pending_confirm=True).intent == "YES"
    assert parse("వద్దు ఆపండి", pending_confirm=True).intent == "NO"


def test_confidence_threshold_low_gives_unknown():
    """Gibberish or empty text gives UNKNOWN with low confidence."""
    empty_res = parse("")
    assert empty_res.intent == "UNKNOWN"
    assert empty_res.confidence == 0.0

    gibberish_res = parse("xyz 123 qqq random meaningless sound")
    assert gibberish_res.intent == "UNKNOWN"
    assert gibberish_res.confidence < 0.4


"""Phase G tests: Forgiving intent matching, fuzzy parsing with rapidfuzz, and tolerance reporting."""

import pytest
from backend.app.services.intent import parse, normalize_text, ParseResult


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
    ("naaku kaavaali tokn raepu", "BOOK", "tomorrow"),          # kaavaali->kavali, tokn->token, raepu->repu
    ("radhu my tokan", "CANCEL", None),                         # radhu->raddu, tokan->token (CANCEL priority)
    ("raddhu cheyandi", "CANCEL", None),                        # raddhu->raddu
    ("pleaz cancle my apointment", "CANCEL", None),             # cancle, apointment
    ("statuss of my queue tokn", "STATUS", None),               # statuss->status, tokn->token (STATUS priority)
    ("wen is my turn", "STATUS", None),                         # wen->when
    ("need a tokn tommorow", "BOOK", "tomorrow"),               # tokn->token, tommorow->tomorrow
    ("yess confirm it", "YES", None),                           # yess->yes
    ("nope do not", "NO", None),                                # nope, do not
    ("doktor apointment kavali ivala", "BOOK", "today"),        # doktor->doctor, apointment->appointment
]


def test_normalization_variants():
    """Verify common romanization variants normalize to standard forms."""
    assert "kavali" in normalize_text("kaavaali")
    assert "kavali" in normalize_text("kavaali")
    assert "repu" in normalize_text("raepu")
    assert "raddu" in normalize_text("radhu")
    assert "raddu" in normalize_text("raddhu")


def test_confidence_and_unknown():
    """Verify confidence below 0.4 returns UNKNOWN."""
    res_empty = parse("")
    assert res_empty.intent == "UNKNOWN"
    assert res_empty.confidence == 0.0

    res_gibberish = parse("xyz abc qqq zzz")
    assert res_gibberish.intent == "UNKNOWN"
    assert res_gibberish.confidence < 0.4

    res_valid = parse("I need a token for tomorrow")
    assert res_valid.intent == "BOOK"
    assert 0.4 <= res_valid.confidence <= 1.0


def test_pending_confirmation_yes_no():
    """When confirmation is pending, YES or NO words anywhere are treated as answer."""
    # YES anywhere in sentence overrides other words
    res_yes = parse("yes please cancel my token", pending_confirm=True)
    assert res_yes.intent == "YES"

    # NO anywhere in sentence overrides other words
    res_no = parse("no don't cancel it", pending_confirm=True)
    assert res_no.intent == "NO"

    # Telugu confirmation
    res_te_yes = parse("అవును రద్దు చేయండి", pending_confirm=True)
    assert res_te_yes.intent == "YES"

    res_te_no = parse("వద్దు ఆపండి", pending_confirm=True)
    assert res_te_no.intent == "NO"


def test_intent_accuracy_and_reporting(capsys):
    """
    Evaluates 15 Telugu, 15 English, 15 Mix, and 10 noisy variants.
    Prints accuracy table and misses for tuning keyword lists.
    """
    categories = {
        "Telugu": TELUGU_PHRASES,
        "English": ENGLISH_PHRASES,
        "Mix": MIX_PHRASES,
        "Noisy Variants": NOISY_VARIANTS,
    }

    results = {}
    all_misses = []
    total_count = 0
    total_passed = 0

    for cat_name, phrases in categories.items():
        cat_total = len(phrases)
        cat_passed = 0
        for text, exp_intent, exp_day in phrases:
            parsed = parse(text)
            intent_ok = (parsed.intent == exp_intent)
            day_ok = (exp_day is None or parsed.day == exp_day)
            if intent_ok and day_ok:
                cat_passed += 1
                total_passed += 1
            else:
                all_misses.append({
                    "category": cat_name,
                    "text": text,
                    "expected_intent": exp_intent,
                    "expected_day": exp_day,
                    "got_intent": parsed.intent,
                    "got_day": parsed.day,
                    "confidence": parsed.confidence,
                })
            total_count += 1
        results[cat_name] = (cat_passed, cat_total, (cat_passed / cat_total) * 100.0)

    # Print summary report
    print("\n" + "=" * 64)
    print("      PHASE G INTENT ACCURACY REPORT (FORGIVING MATCHING)")
    print("=" * 64)
    for cat_name, (passed, total, acc) in results.items():
        print(f"  {cat_name:<16}: {passed:2d}/{total:2d} ({acc:5.1f}%)")
    overall_acc = (total_passed / total_count) * 100.0
    print("-" * 64)
    print(f"  OVERALL         : {total_passed:2d}/{total_count:2d} ({overall_acc:5.1f}%)")
    print("=" * 64)

    if all_misses:
        print("\nMISSES:")
        for m in all_misses:
            print(f"  [{m['category']}] \"{m['text']}\" -> Expected: {m['expected_intent']} (day={m['expected_day']}), Got: {m['got_intent']} (day={m['got_day']}), Conf: {m['confidence']}")
    else:
        print("\nAll phrases passed with 100% accuracy!")
    print("=" * 64 + "\n")

    # Assert accuracy for each category is >= 90%
    for cat_name, (passed, total, acc) in results.items():
        assert acc >= 90.0, f"{cat_name} accuracy is too low: {acc:.1f}%"


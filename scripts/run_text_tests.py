"""Script to run offline NLU text intent accuracy tests against docs/test_phrases.csv."""

import csv
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import settings
from backend.app.services.intent import parse


def run_tests(csv_path: Path = None):
    if csv_path is None:
        csv_path = REPO_ROOT / "docs" / "test_phrases.csv"

    if not csv_path.exists():
        print(f"Error: test phrases file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    # Disable Groq fallback during test run to ensure strict offline rule-based verification
    original_groq = settings.GROQ_API_KEY
    settings.GROQ_API_KEY = ""

    total = 0
    passed = 0
    misses = []

    by_language = {}
    by_intent = {}

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            phrase = row["phrase"].strip()
            lang = row["language"].strip()
            exp_intent = row["expected_intent"].strip()
            exp_day = row.get("expected_day", "").strip() or None

            # Init language stats
            if lang not in by_language:
                by_language[lang] = {"total": 0, "passed": 0}
            by_language[lang]["total"] += 1

            # Init intent stats
            if exp_intent not in by_intent:
                by_intent[exp_intent] = {"total": 0, "passed": 0}
            by_intent[exp_intent]["total"] += 1

            # Run parser without calling Gnani
            result = parse(phrase)
            is_intent_match = (result.intent == exp_intent)
            is_day_match = (exp_day is None or result.day == exp_day) if exp_intent == "BOOK" else True

            if is_intent_match and is_day_match:
                passed += 1
                by_language[lang]["passed"] += 1
                by_intent[exp_intent]["passed"] += 1
            else:
                misses.append({
                    "language": lang,
                    "phrase": phrase,
                    "expected_intent": exp_intent,
                    "expected_day": exp_day,
                    "got_intent": result.intent,
                    "got_day": result.day,
                })

    # Restore Groq key
    settings.GROQ_API_KEY = original_groq

    # Print Report
    overall_acc = (passed / total * 100) if total > 0 else 0.0
    print("=" * 64)
    print("         VOICEQUEUE NLU TEXT ACCURACY REPORT")
    print("=" * 64)
    print(f"Test File        : {csv_path.name}")
    print(f"Total Test Cases : {total}")
    print(f"Overall Accuracy : {passed}/{total} ({overall_acc:.1f}%)\n")

    print("--- Accuracy by Language ---")
    for lang, stats in sorted(by_language.items()):
        acc = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        print(f"  {lang:<10} : {stats['passed']:>2}/{stats['total']:<2} ({acc:.1f}%)")

    print("\n--- Accuracy by Intent ---")
    for intent, stats in sorted(by_intent.items()):
        acc = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        print(f"  {intent:<10} : {stats['passed']:>2}/{stats['total']:<2} ({acc:.1f}%)")

    print("\n--- Misses ---")
    if not misses:
        print("  None! All phrases parsed accurately.")
    else:
        print(f"  Found {len(misses)} miss(es):")
        for m in misses:
            day_info = f" (day exp: {m['expected_day']}, got: {m['got_day']})" if m["expected_day"] else ""
            print(f"  [{m['language']}] \"{m['phrase']}\"")
            print(f"    -> Expected: {m['expected_intent']}, Got: {m['got_intent']}{day_info}")

    print("=" * 64)

    return total, passed, misses


if __name__ == "__main__":
    total, passed, misses = run_tests()
    if misses:
        sys.exit(1)
    sys.exit(0)


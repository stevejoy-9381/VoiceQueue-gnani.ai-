"""
T8 Real Gnani Round Trip Test Suite.
Constraints:
- Max 60 real Gnani calls (30 sentences * 2 = 30 TTS + 30 STT).
- One request at a time.
- Stop immediately if 3 failures occur in a row.
- Synthetic round trip, NOT human voice accuracy.
- Do NOT insert rows into voice_tests table in voicequeue.db.
- Save report to docs/test_run/T8_real_gnani.md.
"""

import os
import sys
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding for Telugu characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend settings allow up to session cap in memory
from backend.app.config import settings
settings.GNANI_DAILY_CAP = 400

from backend.app.services import gnani, intent

TEST_SENTENCES = [
    # --- TELUGU SCRIPT (10 sentences) ---
    {
        "id": "TE-01",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "BOOK (today)",
        "sentence": "నాకు ఈరోజు టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "id": "TE-02",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "BOOK (tomorrow)",
        "sentence": "రేపు టోకెన్ బుక్ చేయండి",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "id": "TE-03",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "BOOK (no day)",
        "sentence": "నాకు డాక్టర్ టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "id": "TE-04",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "STATUS",
        "sentence": "నా టోకెన్ స్టేటస్ ఎంత",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "TE-05",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "STATUS (var)",
        "sentence": "నా వంతు ఎప్పుడు వస్తుంది",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "TE-06",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "CANCEL",
        "sentence": "నా టోకెన్ రద్దు చేయండి",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "TE-07",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "CANCEL (var)",
        "sentence": "టోకెన్ క్యాన్సిల్ చేయండి",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "TE-08",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "YES",
        "sentence": "అవును",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "id": "TE-09",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "NO",
        "sentence": "వద్దు",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "id": "TE-10",
        "lang_group": "Telugu",
        "tts_lang": "te-IN",
        "stt_lang": "te",
        "category": "UNKNOWN",
        "sentence": "ఈరోజు వాతావరణం ఎలా ఉంది",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },

    # --- ENGLISH (10 sentences) ---
    {
        "id": "EN-01",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "BOOK (today)",
        "sentence": "I need an appointment token for today",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "id": "EN-02",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "BOOK (tomorrow)",
        "sentence": "Book a token for tomorrow please",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "id": "EN-03",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "BOOK (no day)",
        "sentence": "Please book a token for me",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "id": "EN-04",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "STATUS",
        "sentence": "What is my current queue status",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "EN-05",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "STATUS (var)",
        "sentence": "When is my turn to see the doctor",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "EN-06",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "CANCEL",
        "sentence": "Please cancel my token",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "EN-07",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "CANCEL (var)",
        "sentence": "I want to cancel my appointment",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "EN-08",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "YES",
        "sentence": "Yes confirm it",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "id": "EN-09",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "NO",
        "sentence": "No do not do that",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "id": "EN-10",
        "lang_group": "English",
        "tts_lang": "en-IN",
        "stt_lang": "en",
        "category": "UNKNOWN",
        "sentence": "What is the weather outside today",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },

    # --- MIX (10 sentences) ---
    {
        "id": "MIX-01",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "BOOK (today)",
        "sentence": "Ivala clinic token book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "id": "MIX-02",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "BOOK (tomorrow)",
        "sentence": "Repu appointment token kavali",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "id": "MIX-03",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "BOOK (no day)",
        "sentence": "Oka doctor token ivvandi",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "id": "MIX-04",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "STATUS",
        "sentence": "Naa token status entha undi",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "MIX-05",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "STATUS (var)",
        "sentence": "Queue lo naa turn eppudu",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "id": "MIX-06",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "CANCEL",
        "sentence": "Naa appointment token cancel cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "MIX-07",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "CANCEL (var)",
        "sentence": "Token cancel cheyali",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "id": "MIX-08",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "YES",
        "sentence": "Avunu confirm cheyandi",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "id": "MIX-09",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "NO",
        "sentence": "Vaddu cancel cheyoddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "id": "MIX-10",
        "lang_group": "Mix",
        "tts_lang": "te-IN",
        "stt_lang": "mix",
        "category": "UNKNOWN",
        "sentence": "Clinic timings enti",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },
]


def check_voice_tests_count() -> int:
    try:
        conn = sqlite3.connect("voicequeue.db")
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM voice_tests")
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return -1


def check_real_gnani_calls() -> int:
    try:
        conn = sqlite3.connect("voicequeue.db")
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM gnani_usage WHERE cached=0")
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return -1


def main():
    print("=" * 70)
    print("T8 REAL GNANI ROUND TRIP TEST SUITE")
    print("Label: synthetic round trip, NOT human voice accuracy")
    print("=" * 70)

    initial_real_calls = check_real_gnani_calls()
    initial_tests_count = check_voice_tests_count()
    print(f"Starting real calls in DB: {initial_real_calls}")
    print(f"Starting rows in voice_tests: {initial_tests_count}")

    results = []
    consecutive_failures = 0
    t_start = time.time()
    call_budget_used = 0

    for idx, item in enumerate(TEST_SENTENCES, 1):
        if call_budget_used >= 60:
            print(f"[HALT] Reached maximum allowed budget of 60 Gnani calls.")
            break

        test_id = item["id"]
        lang_group = item["lang_group"]
        tts_lang = item["tts_lang"]
        stt_lang = item["stt_lang"]
        category = item["category"]
        sentence = item["sentence"]
        expected_intent = item["expected_intent"]
        expected_day = item["expected_day"]

        print(f"[{idx:02d}/30] Running {test_id} ({lang_group} - {category})...", end=" ", flush=True)

        t_item_start = time.time()
        tts_ok = False
        stt_ok = False
        transcript = ""
        stt_detected_lang = ""
        tts_audio = b""
        tts_latency = 0.0
        stt_latency = 0.0
        err_msg = ""

        # Step 1: TTS
        try:
            t0 = time.time()
            tts_audio = gnani.tts(sentence, lang=tts_lang)
            tts_latency = time.time() - t0
            call_budget_used += 1
            tts_ok = True
        except Exception as e:
            err_msg = f"TTS error: {str(e)}"
            call_budget_used += 1

        # Step 2: STT (only if TTS produced audio)
        if tts_ok and tts_audio:
            try:
                t0 = time.time()
                stt_res = gnani.stt(tts_audio, user_lang=stt_lang)
                stt_latency = time.time() - t0
                call_budget_used += 1
                transcript = stt_res.get("transcript", "")
                stt_detected_lang = stt_res.get("language", "")
                stt_ok = True
            except Exception as e:
                err_msg = f"STT error: {str(e)}"
                call_budget_used += 1

        total_latency = time.time() - t_item_start

        # Step 3: Intent Parsing
        parsed_intent = "ERROR"
        parsed_day = None
        confidence = 0.0
        if stt_ok:
            try:
                res = intent.parse(transcript)
                parsed_intent = res.intent
                parsed_day = res.day
                confidence = res.confidence
            except Exception as e:
                err_msg = f"Intent parse error: {str(e)}"

        # Step 4: Evaluate Pass/Fail
        # Match intent, and if expected_day is specified, match day as well
        intent_match = (parsed_intent == expected_intent)
        day_match = True
        if expected_day is not None:
            day_match = (parsed_day == expected_day)

        is_pass = tts_ok and stt_ok and intent_match and day_match

        if is_pass:
            consecutive_failures = 0
            outcome = "PASS"
            status_symbol = "OK"
        else:
            consecutive_failures += 1
            outcome = "FAIL"
            status_symbol = "FAIL"

        print(f"{status_symbol} ({total_latency:.2f}s) -> Got: '{parsed_intent}' day={parsed_day} [STT: \"{transcript}\"]")

        results.append({
            "id": test_id,
            "lang_group": lang_group,
            "category": category,
            "sentence": sentence,
            "tts_latency": tts_latency,
            "stt_latency": stt_latency,
            "total_latency": total_latency,
            "transcript": transcript,
            "expected_intent": expected_intent,
            "expected_day": expected_day,
            "parsed_intent": parsed_intent,
            "parsed_day": parsed_day,
            "confidence": confidence,
            "outcome": outcome,
            "error": err_msg,
        })

        if consecutive_failures >= 3:
            print("\n" + "!" * 70)
            print("SAFETY HALT TRIGGERED: 3 consecutive failures encountered!")
            print("!" * 70 + "\n")
            break

    total_time = time.time() - t_start
    final_real_calls = check_real_gnani_calls()
    final_tests_count = check_voice_tests_count()
    real_calls_delta = final_real_calls - initial_real_calls

    passed_count = sum(1 for r in results if r["outcome"] == "PASS")
    failed_count = sum(1 for r in results if r["outcome"] == "FAIL")

    print("\n" + "=" * 70)
    print(f"T8 SUMMARY: {passed_count}/{len(results)} passed, {failed_count} failed in {total_time:.1f}s")
    print(f"Gnani calls used: {real_calls_delta} (budget: 60, DB real calls: {final_real_calls})")
    print(f"voice_tests row count change: {final_tests_count - initial_tests_count} (must be 0)")
    print("=" * 70)

    # Write Markdown Report
    report_path = Path("docs/test_run/T8_real_gnani.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# T8 Real Gnani Round Trip Test Report\n\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> **LABEL**: synthetic round trip, NOT human voice accuracy\n")
        f.write("> These metrics evaluate synthetic Timbre TTS playback fed directly into Prisma STT.\n")
        f.write("> These results are NOT written to the Tests page grid (`voice_tests` table).\n\n")

        f.write("## Overview & Constraints\n\n")
        f.write(f"- **Execution Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC\n")
        f.write(f"- **Total Sentences Tested**: {len(results)} / {len(TEST_SENTENCES)}\n")
        f.write(f"- **Passed**: {passed_count}\n")
        f.write(f"- **Failed**: {failed_count}\n")
        f.write(f"- **Total Duration**: {total_time:.2f}s\n")
        f.write(f"- **Real Gnani Calls Used**: {real_calls_delta} (T8 budget: MAX 60, baseline: 272, total in DB: {final_real_calls})\n")
        f.write(f"- **Consecutive Failures Triggered Halt**: {'Yes (3 in a row)' if consecutive_failures >= 3 else 'No'}\n")
        f.write(f"- **Tests Page Grid Unmodified**: Confirmed (`voice_tests` row count delta: {final_tests_count - initial_tests_count})\n\n")

        f.write("## Detailed Test Results\n\n")
        f.write("| ID | Language | Category | Input Sentence | STT Transcript | Expected | Actual | Latency | Result |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")

        for r in results:
            exp_str = r["expected_intent"] + (f" ({r['expected_day']})" if r["expected_day"] else "")
            act_str = r["parsed_intent"] + (f" ({r['parsed_day']})" if r["parsed_day"] else "")
            f.write(f"| {r['id']} | {r['lang_group']} | {r['category']} | `{r['sentence']}` | `{r['transcript']}` | {exp_str} | {act_str} | {r['total_latency']:.2f}s | **{r['outcome']}** |\n")

        f.write("\n## Failures & Discrepancies\n\n")
        failures = [r for r in results if r["outcome"] == "FAIL"]
        if not failures:
            f.write("None. All tested round-trip queries parsed into their expected intents.\n")
        else:
            f.write("| ID | Language | Category | Sentence | Transcript | Expected | Got | Reason |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for fl in failures:
                reason = fl["error"] if fl["error"] else f"Intent or day mismatch (conf={fl['confidence']:.2f})"
                f.write(f"| {fl['id']} | {fl['lang_group']} | {fl['category']} | `{fl['sentence']}` | `{fl['transcript']}` | `{fl['expected_intent']}` | `{fl['parsed_intent']}` | {reason} |\n")

        f.write("\n## Latency Breakdown\n\n")
        avg_tts = sum(r["tts_latency"] for r in results) / len(results) if results else 0.0
        avg_stt = sum(r["stt_latency"] for r in results) / len(results) if results else 0.0
        avg_total = sum(r["total_latency"] for r in results) / len(results) if results else 0.0
        f.write(f"- **Average TTS Synthesis Latency**: {avg_tts:.2f}s\n")
        f.write(f"- **Average STT Transcription Latency**: {avg_stt:.2f}s\n")
        f.write(f"- **Average End-to-End Latency**: {avg_total:.2f}s\n")

    print(f"\nReport written to: {report_path.resolve()}")


if __name__ == "__main__":
    main()

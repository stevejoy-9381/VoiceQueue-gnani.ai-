"""T3 Intent Matrix Verification Script
Evaluates rule-based intent parser across 4 languages:
- Telugu script
- Romanized Telugu
- English
- Mix (Telugu + English)
Covers BOOK (today, tomorrow, no day), STATUS, CANCEL, YES, NO, UNKNOWN,
misspellings, negations, numbers, fillers, very long sentences, and unrelated speech.
Label: text-only, no audio.
"""

import sys
from pathlib import Path
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from collections import defaultdict
from backend.app.services.intent import parse

TEST_CASES = [
    # =========================================================================
    # 1. TELUGU SCRIPT (22 inputs)
    # =========================================================================
    {
        "lang": "Telugu script",
        "category": "BOOK (today)",
        "text": "ఈరోజు నాకు టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Telugu script",
        "category": "BOOK (today)",
        "text": "ఈ రోజు డాక్టర్ గారి అపాయింట్మెంట్ బుక్ చేయండి",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Telugu script",
        "category": "BOOK (tomorrow)",
        "text": "రేపు టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu script",
        "category": "BOOK (tomorrow)",
        "text": "రేపటికి అపాయింట్మెంట్ బుక్ చేయండి",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu script",
        "category": "BOOK (no day)",
        "text": "నాకు ఒక టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "BOOK (no day)",
        "text": "టోకెన్ బుక్ చేయండి",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "STATUS",
        "text": "నా టోకెన్ స్టేటస్ ఏమిటి",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "STATUS (numbers)",
        "text": "టోకెన్ నంబర్ 5 ఎప్పుడు వస్తుంది",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "STATUS (fillers)",
        "text": "నమస్తే అండి నా టోకెన్ నంబర్ ఎంతమంది ఉన్నారో చెప్పండి ధన్యవాదాలు",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "CANCEL",
        "text": "టోకెన్ రద్దు చేయండి",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "CANCEL",
        "text": "ఈరోజు అపాయింట్మెంట్ క్యాన్సిల్ చేయండి",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "Telugu script",
        "category": "YES",
        "text": "అవును సరే",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "YES",
        "text": "హా అవును",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "NO",
        "text": "వద్దు చేయొద్దు",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "NO",
        "text": "కాదు వద్దు",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "negation",
        "text": "టోకెన్ రద్దు చేయవద్దు",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "negation",
        "text": "క్యాన్సిల్ వద్దు",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "misspellings",
        "text": "రేపు టోకెన్ కావాలీ ఇవ్వండి",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu script",
        "category": "fillers",
        "text": "నమస్కారం డాక్టర్ గారు దయచేసి నాకు ఈరోజు టోకెన్ ఇవ్వండి",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Telugu script",
        "category": "very long sentences",
        "text": "నమస్కారం డాక్టర్ గారు నాకు నిన్నటి నుండి చాలా తలనొప్పిగా ఉంది కాబట్టి దయచేసి రేపటికి ఒక అపాయింట్మెంట్ బుక్ చేయండి నా పేరు రమేష్",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu script",
        "category": "unrelated speech",
        "text": "హైదరాబాద్ వాతావరణం ఎలా ఉంది",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },
    {
        "lang": "Telugu script",
        "category": "unrelated speech",
        "text": "ఈరోజు క్రికెట్ మ్యాచ్ ఎవరు గెలిచారు",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },

    # =========================================================================
    # 2. ROMANIZED TELUGU (22 inputs)
    # =========================================================================
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (today)",
        "text": "ee roju naaku token kavali",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (today)",
        "text": "ivala appointment kavali",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (tomorrow)",
        "text": "repu naaku token kavali",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (tomorrow)",
        "text": "repatiki token ivvandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (no day)",
        "text": "naaku oka token kavali",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "BOOK (no day)",
        "text": "token teesukovali",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "STATUS",
        "text": "naa token status entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "STATUS (numbers)",
        "text": "token number seven eppudu vastundi",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "STATUS (numbers)",
        "text": "naa token number 4 entha mandi unnaru",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "CANCEL",
        "text": "token raddu cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "CANCEL",
        "text": "ee roju appointment raddu cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "Romanized Telugu",
        "category": "YES",
        "text": "avunu sare",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "YES",
        "text": "haa correct",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "NO",
        "text": "vaddu cheyyoddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "NO",
        "text": "kaadu vaddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "negation",
        "text": "token cancel cheyyoddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "negation",
        "text": "raddu vaddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "misspellings",
        "text": "repu tokn kaavli",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Romanized Telugu",
        "category": "misspellings",
        "text": "token radhu cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Romanized Telugu",
        "category": "fillers",
        "text": "namaskaram andi dayachesi repatiki oka token ivvandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Romanized Telugu",
        "category": "very long sentences",
        "text": "namaste doctor garu naaku koddiga ontlo bagoledu andukani ivala doctor garini kalavali oka token ivvagalara please",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Romanized Telugu",
        "category": "unrelated speech",
        "text": "cinemaki veldam anukuntunnanu ticket entha",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },

    # =========================================================================
    # 3. ENGLISH (24 inputs)
    # =========================================================================
    {
        "lang": "English",
        "category": "BOOK (today)",
        "text": "book an appointment today",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "English",
        "category": "BOOK (today)",
        "text": "I want a token today",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "English",
        "category": "BOOK (tomorrow)",
        "text": "I need a token for tomorrow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "BOOK (tomorrow)",
        "text": "please book an appointment for tomorrow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "BOOK (no day)",
        "text": "I want to book a token please",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "BOOK (no day)",
        "text": "need an appointment",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "STATUS",
        "text": "what is my token status",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "STATUS",
        "text": "when is my turn",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "STATUS (numbers)",
        "text": "token number seven",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "STATUS (numbers)",
        "text": "status of token 12 please",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "CANCEL",
        "text": "cancel my token",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "CANCEL",
        "text": "remove my appointment for today",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "English",
        "category": "YES",
        "text": "yes please confirm",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "YES",
        "text": "yeah okay sure",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "NO",
        "text": "no thank you",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "NO",
        "text": "nope never",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "negation",
        "text": "do not cancel my token",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "negation",
        "text": "please don't cancel my appointment",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "misspellings",
        "text": "please bok tokn for me tomorow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "misspellings",
        "text": "i want to cancle my appointment",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "misspellings",
        "text": "check sttatus of my tokn",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "fillers",
        "text": "hello good morning sir can you please give me a token for tomorrow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "very long sentences",
        "text": "good morning doctor could you please book an appointment for tomorrow my name is Robert Brown",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "unrelated speech",
        "text": "what is the weather outside right now",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },

    # =========================================================================
    # 4. MIX (TELUGU + ENGLISH) (24 inputs)
    # =========================================================================
    {
        "lang": "Mix",
        "category": "BOOK (today)",
        "text": "ee roju token book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "BOOK (today)",
        "text": "ivala appointment book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "BOOK (tomorrow)",
        "text": "repu naaku token book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "BOOK (tomorrow)",
        "text": "tomorrow clinic token kavali",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "BOOK (no day)",
        "text": "clinic lo token book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "BOOK (no day)",
        "text": "doctor appointment kavali",
        "expected_intent": "BOOK",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "STATUS",
        "text": "my token status entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "STATUS",
        "text": "queue lo entha mandi ahead unnaru",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "STATUS (numbers)",
        "text": "token number seven eppudu",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "STATUS (numbers)",
        "text": "token 15 status entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "CANCEL",
        "text": "token cancel cheyandi please",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "CANCEL",
        "text": "appointment delete cheyandi please",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "YES",
        "text": "yes avunu confirm",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "YES",
        "text": "okay sare",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "NO",
        "text": "no vaddu stop",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "NO",
        "text": "no kaadu cheyyoddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "negation",
        "text": "please token cancel cheyyaku",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "negation",
        "text": "don't cancel, token unchandi",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "misspellings",
        "text": "repu tokn bok cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "misspellings",
        "text": "tokn cancle cheyyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "fillers",
        "text": "Good morning andi, can you give me one token for tomorrow clinic appointment?",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "very long sentences",
        "text": "Hello doctor garu, can you please book a token for me tomorrow? Naa peru Krishna.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "very long sentences",
        "text": "Hello sir, please cancel my token today, i cannot come to clinic.",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "unrelated speech",
        "text": "cricket score entha tell me",
        "expected_intent": "UNKNOWN",
        "expected_day": None,
    },
]

def run_tests():
    print(f"Total inputs to test: {len(TEST_CASES)}")
    stats = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0})
    results = []

    for i, tc in enumerate(TEST_CASES, 1):
        lang = tc["lang"]
        text = tc["text"]
        exp_intent = tc["expected_intent"]
        exp_day = tc["expected_day"]

        res = parse(text)
        actual_intent = res.intent
        actual_day = res.day

        intent_pass = (actual_intent == exp_intent)
        day_pass = (actual_day == exp_day)
        passed = intent_pass and day_pass

        stats[lang]["total"] += 1
        if passed:
            stats[lang]["pass"] += 1
            status_str = "PASS"
        else:
            stats[lang]["fail"] += 1
            status_str = "FAIL"

        results.append({
            "idx": i,
            "lang": lang,
            "category": tc["category"],
            "text": text,
            "expected_intent": exp_intent,
            "expected_day": exp_day,
            "actual_intent": actual_intent,
            "actual_day": actual_day,
            "confidence": res.confidence,
            "result": status_str,
        })

    print("\n--- RESULTS BY LANGUAGE (text-only, no audio) ---")
    overall_total = 0
    overall_pass = 0
    overall_fail = 0

    for lang in ["Telugu script", "Romanized Telugu", "English", "Mix"]:
        d = stats[lang]
        tot = d["total"]
        p = d["pass"]
        f = d["fail"]
        acc = (p / tot * 100.0) if tot > 0 else 0.0
        overall_total += tot
        overall_pass += p
        overall_fail += f
        print(f"{lang:18}: Total={tot:2d} | Passed={p:2d} | Failed={f:2d} | Accuracy={acc:6.1f}%")

    print("-" * 65)
    overall_acc = (overall_pass / overall_total * 100.0) if overall_total > 0 else 0.0
    print(f"OVERALL           : Total={overall_total:2d} | Passed={overall_pass:2d} | Failed={overall_fail:2d} | Accuracy={overall_acc:6.1f}%")

    fails = [r for r in results if r["result"] == "FAIL"]
    print(f"\nTotal FAIL count: {len(fails)}")
    if fails:
        print("\n--- LIST OF ALL FAILS ---")
        for f in fails:
            print(f"[{f['idx']}] Lang: {f['lang']} | Cat: {f['category']}")
            print(f"    Text: {f['text']}")
            print(f"    Expected: intent={f['expected_intent']}, day={f['expected_day']}")
            print(f"    Got:      intent={f['actual_intent']}, day={f['actual_day']} (conf={f['confidence']})")

    return results, stats

if __name__ == "__main__":
    results, stats = run_tests()

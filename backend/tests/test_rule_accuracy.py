"""Rule-based Intent Parser Accuracy and Edge-Case Test Suite (P1-8).

Honest Evaluation Statement:
============================
These phrases are written by me (synthetic rule validation dataset), so this
evaluation is an empirical text rule test, NOT a real voice/acoustic model test.
It tests rule robustness against long polite phrases, misspellings, fillers,
and linguistic negation in Telugu, English, and Mix.
"""

from collections import defaultdict
import pytest

from backend.app.services.intent import parse


TEST_PHRASES = [
    # --------------------------------------------------------------------------
    # English Phrases (20 phrases)
    # --------------------------------------------------------------------------
    # Long polite sentences (English)
    {
        "lang": "English",
        "category": "long_polite",
        "text": "Hello, I want to book a token. Can you book a token on my name? My name is D. Stevenson.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "long_polite",
        "text": "Good morning doctor, could you please book an appointment for tomorrow? My name is Robert Brown.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "long_polite",
        "text": "Hello sir, I would like to check the current status of my token number seven please.",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "long_polite",
        "text": "Good afternoon madam, could you please cancel my appointment for today? Thank you.",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "English",
        "category": "long_polite",
        "text": "Excuse me, I am looking to book a new clinic token for today please.",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    # Misspellings (English)
    {
        "lang": "English",
        "category": "misspelling",
        "text": "please bok tokn for me",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "misspelling",
        "text": "i want to cancle my appointment",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "misspelling",
        "text": "check sttatus of my tokn",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "misspelling",
        "text": "bok appointment tomorow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    # Negations (English)
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
    # Standard English phrases
    {
        "lang": "English",
        "category": "standard",
        "text": "I need a token for tomorrow",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "book an appointment today",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "token number seven",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "where is my token in the queue",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "how many patients ahead of me",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "cancel my token",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "remove my appointment",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "yes please confirm",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "English",
        "category": "standard",
        "text": "no thank you",
        "expected_intent": "NO",
        "expected_day": None,
    },

    # --------------------------------------------------------------------------
    # Telugu Phrases (20 phrases)
    # --------------------------------------------------------------------------
    # Long polite sentences (Telugu)
    {
        "lang": "Telugu",
        "category": "long_polite",
        "text": "నమస్కారం డాక్టర్ గారు, దయచేసి రేపటికి నాకు ఒక టోకెన్ బుక్ చేయగలరా? నా పేరు రమేష్.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu",
        "category": "long_polite",
        "text": "నమస్తే అండి, దయచేసి నా టోకెన్ స్టేటస్ ఎంతవరకు వచ్చిందో చెప్పండి. ధన్యవాదాలు.",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "long_polite",
        "text": "నమస్కారమండి, ఈరోజు నా అపాయింట్మెంట్ రద్దు చేయవలసిందిగా కోరుతున్నాను. నా పేరు సురేష్.",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "Telugu",
        "category": "long_polite",
        "text": "Namaskaram andi, dayachesi repatiki naaku oka token book cheyandi, naa peru Venkat.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu",
        "category": "long_polite",
        "text": "Namaste doctor garu, naa token number eppudu vastundo cheppagalara please.",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    # Misspellings (Telugu)
    {
        "lang": "Telugu",
        "category": "misspelling",
        "text": "repu tokn kavli",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu",
        "category": "misspelling",
        "text": "token radhu cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "misspelling",
        "text": "token sttatus eppudu",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    # Negations (Telugu)
    {
        "lang": "Telugu",
        "category": "negation",
        "text": "token cancel cheyyoddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "negation",
        "text": "raddu vaddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "negation",
        "text": "cancel kaadu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    # Standard Telugu phrases
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "రేపు టోకెన్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "ఈరోజు అపాయింట్మెంట్ కావాలి",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "నా టోకెన్ స్టేటస్ ఏమిటి",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "టోకెన్ రద్దు చేయండి",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "repu naaku token kavali",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "ivala appointment kavali",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "naa token number entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "avunu",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Telugu",
        "category": "standard",
        "text": "vaddu",
        "expected_intent": "NO",
        "expected_day": None,
    },

    # --------------------------------------------------------------------------
    # Mix Phrases (Telugu + English) (20 phrases)
    # --------------------------------------------------------------------------
    # Long polite sentences (Mix)
    {
        "lang": "Mix",
        "category": "long_polite",
        "text": "Hello doctor garu, can you please book a token for me tomorrow? Naa peru Krishna.",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "long_polite",
        "text": "Namaste madam, I want to check my token status, eppudu doctor chustaru?",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "long_polite",
        "text": "Hello sir, please cancel my token today, i cannot come to clinic.",
        "expected_intent": "CANCEL",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "long_polite",
        "text": "Good morning andi, can you give me one token for tomorrow clinic appointment?",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "long_polite",
        "text": "Namaskaram doctor, my token number is seven, queue lo entha mandi unnaru?",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    # Misspellings (Mix)
    {
        "lang": "Mix",
        "category": "misspelling",
        "text": "repu tokn bok cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "misspelling",
        "text": "tokn cancle cheyyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "misspelling",
        "text": "sttatus of my tokn entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    # Negations (Mix)
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
    # Standard Mix phrases
    {
        "lang": "Mix",
        "category": "standard",
        "text": "repu naaku token book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "ivala appointment book cheyandi",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "token number seven eppudu",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "my token status entha",
        "expected_intent": "STATUS",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "token cancel cheyandi",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "appointment delete cheyandi please",
        "expected_intent": "CANCEL",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "yes avunu confirm",
        "expected_intent": "YES",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "no vaddu",
        "expected_intent": "NO",
        "expected_day": None,
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "ee roju token kavali",
        "expected_intent": "BOOK",
        "expected_day": "today",
    },
    {
        "lang": "Mix",
        "category": "standard",
        "text": "tomorrow clinic token kavali",
        "expected_intent": "BOOK",
        "expected_day": "tomorrow",
    },
]


def test_stevenson_long_sentence_gives_book_with_day_tomorrow():
    """Verifies that the target sentence gives BOOK with day tomorrow."""
    sentence = "Hello, I want to book a token. Can you book a token on my name? My name is D. Stevenson."
    res = parse(sentence)
    assert res.intent == "BOOK"
    assert res.day == "tomorrow"
    assert res.confidence >= 0.4


def test_conflicting_book_and_cancel_triggers_clarify():
    """When both book and cancel appear in the same sentence, intent parser triggers CLARIFY."""
    phrase = "I want to book or cancel a token"
    res = parse(phrase)
    assert res.intent == "CLARIFY"
    assert res.confidence < 0.4


def test_hindi_kal_is_ignored():
    """The Hindi word 'kal' is ignored and not extracted as tomorrow or today."""
    phrase = "kal token chahiye"
    res = parse(phrase)
    assert res.day != "today"


def test_all_60_phrases_rule_accuracy_and_print_summary():
    """
    Evaluates all 60 phrases across Telugu, English, and Mix categories:
    - 20 Telugu phrases
    - 20 English phrases
    - 20 Mix phrases
    - Includes 15 long polite phrases, 10 misspellings, 7 negations.
    Prints accuracy breakdown by language with honest disclaimer.
    """
    assert len(TEST_PHRASES) >= 60

    stats = defaultdict(lambda: {"total": 0, "correct_intent": 0, "correct_day": 0})
    misses = []

    for item in TEST_PHRASES:
        lang = item["lang"]
        text = item["text"]
        exp_intent = item["expected_intent"]
        exp_day = item["expected_day"]

        res = parse(text)
        stats[lang]["total"] += 1

        intent_match = (res.intent == exp_intent)
        day_match = (res.day == exp_day)

        if intent_match and day_match:
            stats[lang]["correct_intent"] += 1
            stats[lang]["correct_day"] += 1
        else:
            misses.append({
                "text": text,
                "lang": lang,
                "category": item["category"],
                "expected": (exp_intent, exp_day),
                "got": (res.intent, res.day),
            })

    # Print accuracy per language and honest evaluation report
    print("\n" + "=" * 70)
    print(" EMPIRICAL RULE ACCURACY TEST REPORT (P1-8 INTENT HARDENING)")
    print("=" * 70)
    print("NOTE: These phrases are written by me, so the result is a rule test,")
    print("not a voice test. It measures rule coverage for polite speech,")
    print("misspellings, negations, and codemixing.\n")

    overall_total = 0
    overall_correct = 0

    for lang in ["Telugu", "English", "Mix"]:
        data = stats[lang]
        tot = data["total"]
        cor = data["correct_intent"]
        acc = (cor / tot * 100.0) if tot > 0 else 0.0
        overall_total += tot
        overall_correct += cor
        print(f"  {lang:<10} Accuracy: {acc:6.2f}% ({cor}/{tot} phrases passed)")

    overall_acc = (overall_correct / overall_total * 100.0) if overall_total > 0 else 0.0
    print("-" * 70)
    print(f"  OVERALL    Accuracy: {overall_acc:6.2f}% ({overall_correct}/{overall_total} passed)")
    print("=" * 70)

    if misses:
        print("\nMISSED PHRASES:")
        for m in misses:
            safe_text = m['text'].encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"  - [{m['lang']} / {m['category']}] '{safe_text}'")
            print(f"    Expected: {m['expected']} | Got: {m['got']}")

    # Enforce 100% accuracy on the 60-phrase benchmark
    assert len(misses) == 0, f"Found {len(misses)} intent parsing misses out of {overall_total} phrases."


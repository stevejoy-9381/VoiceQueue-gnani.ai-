"""Tests for intent parser, number words, and bilingual replies (Telugu and English)."""

import re
import pytest

from backend.app.services.intent import parse
from backend.app.services.number_words import to_english, to_telugu, to_words
from backend.app.services.replies import (
    booked,
    cancel_confirm,
    cancelled,
    no_token,
    service_paused,
    status,
    unknown,
)


# --- 1. INTENT PARSER TESTS ---
@pytest.mark.parametrize(
    "text,expected_intent,expected_day",
    [
        # Telugu cases
        ("Naaku repu token kavali", "BOOK", "tomorrow"),
        ("నాకు ఈరోజు డాక్టర్ గారి టోకెన్ కావాలి", "BOOK", "today"),
        ("ఈరోజు అపాయింట్మెంట్ బుక్ చేయండి", "BOOK", "today"),
        ("రేపు టోకెన్ కావాలి", "BOOK", "tomorrow"),
        ("టోకెన్ బుక్ చేయండి", "BOOK", "tomorrow"),  # Default day for BOOK is tomorrow
        ("నా నంబర్ ఎప్పుడు వస్తుంది?", "STATUS", None),
        ("ఎంతమంది వేచి ఉన్నారు?", "STATUS", None),
        ("టోకెన్ రద్దు చేయండి", "CANCEL", None),
        ("క్యాన్సిల్ చేయండి ప్లీజ్", "CANCEL", None),
        ("అవును సరే", "YES", None),
        ("వద్దు కాదు", "NO", None),
        # English cases
        ("I need a token for tomorrow", "BOOK", "tomorrow"),
        ("I want a token today", "BOOK", "today"),
        ("Book an appointment now", "BOOK", "today"),
        ("Book a token", "BOOK", "tomorrow"),  # Default day tomorrow
        ("What is my number", "STATUS", None),
        ("When is my turn", "STATUS", None),
        ("How many ahead in queue", "STATUS", None),
        ("How long is the queue position", "STATUS", None),
        ("Please cancel my token", "CANCEL", None),
        ("Delete my appointment", "CANCEL", None),
        ("Remove my token", "CANCEL", None),
        ("Yes yeah confirm", "YES", None),
        ("Okay sure", "YES", None),
        ("No nope do not", "NO", None),
        ("Don't stop", "NO", None),
        # Priority test: CANCEL over BOOK/STATUS
        ("Booked token cancel please", "CANCEL", None),
        ("My status cancel", "CANCEL", None),
        # Priority test: STATUS over BOOK
        ("Token number status please", "STATUS", None),
        # Messy / noisy text
        ("... !!! today ee roju appointment ... ???", "BOOK", "today"),
        ("unknown phrase blah blah blorp", "UNKNOWN", None),
    ],
)
def test_intent_parser(text, expected_intent, expected_day):
    res = parse(text)
    assert res.intent == expected_intent
    assert res.day == expected_day


def test_specific_prompt_requirements():
    res1 = parse("Naaku repu token kavali")
    assert res1.intent == "BOOK"
    assert res1.day == "tomorrow"

    res2 = parse("When is my turn")
    assert res2.intent == "STATUS"

    res3 = parse("need a token")
    assert res3.intent == "BOOK"
    assert res3.day == "tomorrow"


# --- 2. NUMBER WORDS TESTS ---
def test_number_words_telugu():
    assert to_telugu(0) == "సున్నా"
    assert to_telugu(1) == "ఒకటి"
    assert to_telugu(5) == "ఐదు"
    assert to_telugu(10) == "పది"
    assert to_telugu(15) == "పదిహేను"
    assert to_telugu(20) == "ఇరవై"
    assert to_telugu(24) == "ఇరవై నాలుగు"
    assert to_telugu(99) == "తొంభై తొమ్మిది"
    # Greater than 99 returns string of digits
    assert to_telugu(100) == "100"
    assert to_telugu(125) == "125"


def test_number_words_english():
    assert to_english(0) == "zero"
    assert to_english(1) == "one"
    assert to_english(7) == "seven"
    assert to_english(10) == "ten"
    assert to_english(11) == "eleven"
    assert to_english(21) == "twenty one"
    assert to_english(50) == "fifty"
    assert to_english(99) == "ninety nine"
    # Greater than 99 returns digits
    assert to_english(101) == "101"


def test_to_words_dispatch():
    assert to_words(3, "te-IN") == "మూడు"
    assert to_words(3, "en-IN") == "three"


# --- 3. REPLIES AND CACHING TESTS ---
def test_replies_no_digits_inside():
    digit_regex = re.compile(r"\d")

    # Booked (Telugu and English)
    t_book_te, k_book_te = booked(5, "today", "te-IN")
    assert "ఐదు" in t_book_te
    assert "ఈరోజు" in t_book_te
    assert k_book_te is None
    assert not digit_regex.search(t_book_te)

    t_book_en, k_book_en = booked(1, "tomorrow", "en-IN")
    assert "one" in t_book_en
    assert "tomorrow" in t_book_en
    assert "Your token for tomorrow is number one. Please come to the clinic on time." == t_book_en
    assert k_book_en is None
    assert not digit_regex.search(t_book_en)

    # Status
    t_stat_te, k_stat_te = status(7, 2, "te-IN")
    assert "ఏడు" in t_stat_te
    assert "రెండు" in t_stat_te
    assert k_stat_te is None
    assert not digit_regex.search(t_stat_te)

    t_stat_en, k_stat_en = status(7, 2, "en-IN")
    assert "seven" in t_stat_en
    assert "two" in t_stat_en
    assert k_stat_en is None
    assert not digit_regex.search(t_stat_en)

    # Cancel Confirm
    t_conf, k_conf = cancel_confirm(4, "en-IN")
    assert "four" in t_conf
    assert k_conf is None
    assert not digit_regex.search(t_conf)


def test_fixed_replies_have_cache_keys():
    t_can_te, k_can_te = cancelled("te-IN")
    assert k_can_te == "cancelled_te"

    t_can_en, k_can_en = cancelled("en-IN")
    assert k_can_en == "cancelled_en"

    t_not_te, k_not_te = no_token("te-IN")
    assert k_not_te == "no_token_te"

    t_unk_en, k_unk_en = unknown("en-IN")
    assert k_unk_en == "unknown_en"

    t_pau_te, k_pau_te = service_paused("te-IN")
    assert k_pau_te == "service_paused_te"

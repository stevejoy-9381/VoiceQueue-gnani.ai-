"""Phase T1 - Number Words (0-99) and Reply Template Validation Tests.

Tests:
1. Every number 0 to 99 in Telugu contains no digits.
2. Every number 0 to 99 in English contains no digits.
3. Every reply generator in replies.py exists for both te-IN and en-IN.
4. Dynamic replies (booked, status, cancel_confirm) convert digits to spoken words (no digits in text).
5. Static fixed replies return the exact expected cache_key (e.g. 'greeting_te', 'greeting_en').
"""

import re
import pytest

from backend.app.services.number_words import to_english, to_telugu, to_words
from backend.app.services.replies import (
    FIXED_PHRASE_GENERATORS,
    booked,
    cancel_aborted,
    cancel_confirm,
    cancelled,
    greeting,
    no_speech,
    no_token,
    say_again,
    service_paused,
    status,
    too_quiet,
    unknown,
)


def test_telugu_number_words_0_to_99():
    """All numbers 0-99 in Telugu return valid spoken words without digits."""
    for n in range(100):
        word = to_telugu(n)
        assert word and isinstance(word, str)
        assert not re.search(r"\d", word), f"to_telugu({n}) returned digits: '{word}'"

    # Edge cases
    assert to_telugu(0) == "సున్నా"
    assert to_telugu(1) == "ఒకటి"
    assert to_telugu(20) == "ఇరవై"
    assert to_telugu(21) == "ఇరవై ఒకటి"
    assert to_telugu(99) == "తొంభై తొమ్మిది"


def test_english_number_words_0_to_99():
    """All numbers 0-99 in English return valid spoken words without digits."""
    for n in range(100):
        word = to_english(n)
        assert word and isinstance(word, str)
        assert not re.search(r"\d", word), f"to_english({n}) returned digits: '{word}'"

    # Edge cases
    assert to_english(0) == "zero"
    assert to_english(1) == "one"
    assert to_english(13) == "thirteen"
    assert to_english(20) == "twenty"
    assert to_english(42) == "forty two"
    assert to_english(99) == "ninety nine"


def test_number_words_dispatcher():
    """to_words dispatches correctly by language code."""
    assert to_words(5, "te-IN") == "ఐదు"
    assert to_words(5, "en-IN") == "five"
    assert to_words(5, "mix") == "five"


def test_fixed_phrase_templates_and_cache_keys():
    """Every fixed phrase exists for te and en and returns the correct cache key."""
    for name, gen_func in FIXED_PHRASE_GENERATORS.items():
        # Telugu check
        text_te, key_te = gen_func("te-IN")
        assert text_te and isinstance(text_te, str)
        assert key_te == f"{name}_te"
        assert not re.search(r"\d", text_te)

        # English check
        text_en, key_en = gen_func("en-IN")
        assert text_en and isinstance(text_en, str)
        assert key_en == f"{name}_en"
        assert not re.search(r"\d", text_en)


def test_dynamic_reply_templates_contain_no_digits():
    """Dynamic replies with numbers (booked, status, cancel_confirm) contain NO digits."""
    test_numbers = [1, 5, 12, 20, 35, 99]

    for num in test_numbers:
        # booked
        for day in ("today", "tomorrow"):
            for lang in ("te-IN", "en-IN"):
                text, key = booked(num, day, lang)
                assert key is None, "booked() should not return a static cache_key"
                assert not re.search(r"\d", text), f"booked({num}, {day}, {lang}) has digits: '{text}'"

        # status
        for ahead in (0, 1, 4):
            for lang in ("te-IN", "en-IN"):
                text, key = status(num, ahead, lang)
                assert key is None
                assert not re.search(r"\d", text), f"status({num}, {ahead}, {lang}) has digits: '{text}'"

        # cancel_confirm
        for lang in ("te-IN", "en-IN"):
            text, key = cancel_confirm(num, lang)
            assert key is None
            assert not re.search(r"\d", text), f"cancel_confirm({num}, {lang}) has digits: '{text}'"


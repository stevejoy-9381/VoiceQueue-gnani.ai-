# NEEDS NATIVE SPEAKER REVIEW (Telugu numbers)
"""Converts numbers 0 to 99 into spoken words in Telugu and English for TTS."""

TELUGU_0_TO_19 = [
    "సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు",
    "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది",
    "పది", "పదకొండు", "పన్నెండు", "పదమూడు", "పద్నాలుగు",
    "పదిహేను", "పదహారు", "పదిహేడు", "పద్దెనిమిది", "పందొమ్మిది",
]

TELUGU_TENS = {
    20: "ఇరవై",
    30: "ముప్పై",
    40: "నలభై",
    50: "యాభై",
    60: "అరవై",
    70: "డెబ్బై",
    80: "ఎనభై",
    90: "తొంభై",
}

ENGLISH_0_TO_19 = [
    "zero", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]

ENGLISH_TENS = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}


def to_telugu(n: int) -> str:
    """Converts an integer 0-99 to Telugu spoken words. For >99, returns digits."""
    if n < 0 or n > 99:
        return str(n)
    if n < 20:
        return TELUGU_0_TO_19[n]
    tens = (n // 10) * 10
    remainder = n % 10
    if remainder == 0:
        return TELUGU_TENS[tens]
    return f"{TELUGU_TENS[tens]} {TELUGU_0_TO_19[remainder]}"


def to_english(n: int) -> str:
    """Converts an integer 0-99 to English spoken words. For >99, returns digits."""
    if n < 0 or n > 99:
        return str(n)
    if n < 20:
        return ENGLISH_0_TO_19[n]
    tens = (n // 10) * 10
    remainder = n % 10
    if remainder == 0:
        return ENGLISH_TENS[tens]
    return f"{ENGLISH_TENS[tens]} {ENGLISH_0_TO_19[remainder]}"


def to_words(n: int, lang: str = "te-IN") -> str:
    """Dispatches to Telugu or English spoken words based on language code."""
    if lang.startswith("te"):
        return to_telugu(n)
    return to_english(n)

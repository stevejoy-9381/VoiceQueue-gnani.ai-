"""Privacy and Personal Data Masking Service.

Redacts Personally Identifiable Information (PII) before storage in voice logs
or submission to external LLM services:
- Phone numbers (10 digits, with/without spaces/dashes, +91 or 0 prefix) -> [masked]
- Aadhaar numbers (12 digits with or without spaces/dashes) -> [masked]
- PAN numbers (5 letters, 4 digits, 1 letter) -> [masked]
- Email addresses -> [masked]
- Names following trigger phrases ('my name is', 'I am', 'this is', 'naa peru', 'nenu') -> [name]
"""

import re

# PII Patterns
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
AADHAAR_REGEX_SPACED = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
AADHAAR_REGEX_PLAIN = re.compile(r"\b\d{12}\b")
PAN_REGEX = re.compile(r"\b[A-Za-z]{5}\s*\d{4}\s*[A-Za-z]\b")

# Phone patterns (10 digits with optional +91, 91, or 0, with or without spaces/dashes)
PHONE_REGEX_PREFIXED = re.compile(
    r"(?:\+91[\s-]?)?\b(?:91[\s-]?|0[\s-]?)?[6-9]\d(?:\s*-?\s*\d){8}\b"
)
PHONE_REGEX_GENERIC = re.compile(
    r"(?:\+?91[\s-]?)?\b(?:0[\s-]?)?(?:\d[\s-]?){10}\b"
)

# Name trigger phrases (English & Telugu Latin/Script)
NAME_TRIGGERS = [
    r"my\s+name\s+is",
    r"i\s+am",
    r"i[\x27\x60]?m",
    r"this\s+is",
    r"naa\s+peru",
    r"\u0C28\u0C3E\s*\u0C2A\u0C47\u0C30\u0C41",
    r"nenu",
    r"\u0C28\u0C47\u0C28\u0C41",
]

# Stop words that denote end of name and beginning of next phrase/clause
NAME_STOP_WORDS = {
    "and", "i", "need", "want", "looking", "here", "for", "please", "can", "give", "book",
    "my", "a", "to", "the", "appointment", "token", "clinic", "status", "cancel",
    "kavali", "ani", "repu", "ivala", "naaku", "garu", "nunchi", "andi", "undi", "vachanu",
    "కావాలి", "అని", "రేపు", "ఇవాళ", "నాకు", "టోకెన్", "గారు", "నుంచి", "అండి", "ఉంది",
}


def mask_text(text: str) -> str:
    """
    Masks PII from transcript text:
    - Phone, Aadhaar, PAN, and Email replaced with '[masked]'
    - Words after name trigger phrases replaced with '[name]'
    """
    if not text or not text.strip():
        return text or ""

    result = text

    # 1. Mask Email addresses
    result = EMAIL_REGEX.sub("[masked]", result)

    # 2. Mask Aadhaar numbers (12 digits)
    result = AADHAAR_REGEX_SPACED.sub("[masked]", result)
    result = AADHAAR_REGEX_PLAIN.sub("[masked]", result)

    # 3. Mask PAN numbers
    result = PAN_REGEX.sub("[masked]", result)

    # 4. Mask Phone numbers
    result = PHONE_REGEX_PREFIXED.sub("[masked]", result)
    result = PHONE_REGEX_GENERIC.sub("[masked]", result)

    # 5. Mask Names following trigger phrases
    for trigger in NAME_TRIGGERS:
        pattern = re.compile(
            rf"(\b(?:{trigger})\s+)([^\s,;.?!]+(?:\s+[^\s,;.?!]+){{0,2}})",
            re.IGNORECASE,
        )

        def _name_replacer(m: re.Match) -> str:
            prefix = m.group(1)
            candidate = m.group(2)
            words = candidate.split()
            matched_words = []
            leftover_words = []

            for w in words:
                # Strip non-alphanumeric chars for stop word comparison
                clean_w = re.sub(r"[^a-zA-Z\u0C00-\u0C7F]", "", w).lower()
                if clean_w in NAME_STOP_WORDS and matched_words:
                    leftover_words.append(w)
                elif not leftover_words:
                    matched_words.append(w)
                else:
                    leftover_words.append(w)

            if matched_words:
                replacement = f"{prefix}[name]"
                if leftover_words:
                    replacement = f"{replacement} {' '.join(leftover_words)}"
                return replacement
            return m.group(0)

        result = pattern.sub(_name_replacer, result)

    return result


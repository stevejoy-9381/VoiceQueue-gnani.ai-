"""Rule-based forgiving intent parser and slot extractor for Telugu, English, and Mix (P1-8).

Features:
- Filters greetings, polite words, and fillers in English, Romanized Telugu, and Telugu script.
- Redacts/removes masked name phrases (from P1-7) before matching.
- Keyword scoring per intent with fuzzy matching (rapidfuzz), tie-broken by CANCEL > STATUS > BOOK.
- Negation handling: 'do not cancel', 'don't cancel', 'cancel vaddu', 'cheyyoddu', 'kaadu'.
- Status detection for 'token number seven', 'token 7', 'my token', 'naa token'.
- Day words: today, tomorrow, repu, ivala, ee roju, native script. 'kal' is ignored.
- Conflicting actions (both book and cancel present) triggers CLARIFY with cached clarifying reply.
- Low confidence (< 0.4) gives UNKNOWN / say-again reply.
"""

import json
import re
from typing import NamedTuple, Optional
import httpx
from rapidfuzz import fuzz

from backend.app.config import settings
from backend.app.services import privacy

# Polite words, greetings, and fillers to ignore before matching
POLITE_PATTERNS = [
    # English greetings & pleasantries
    r"\b(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\b",
    r"\b(?:please|pls|kindly)\b",
    r"\b(?:can\s+you|could\s+you|would\s+you|will\s+you|can\s+i|may\s+i|i\s+want\s+to|i\s+would\s+like\s+to|i\s+need\s+to)\b",
    r"\b(?:sir|madam|maam|mam)\b",
    r"\b(?:doctor|dr|doc|daktar|dactar|\u0C21\u0C3E\u0C15\u0C4D\u0C1F\u0C30\u0C4D)\b",
    r"\b(?:thank\s+you|thanks|thank\s+u)\b",
    r"\b(?:excuse\s+me|help\s+me|help)\b",
    # Telugu romanized pleasantries
    r"\b(?:namaskaram|namaste|namaskaramandi|vandanalu)\b",
    r"\b(?:dayachesi|dayavunchi)\b",
    r"\b(?:cheppandi|cheppagalara|cheyagalara|ivvagalara)\b",
    r"\b(?:garu|andi)\b",
    r"\b(?:dhanyavadalu)\b",
    # Telugu script pleasantries
    r"(?:\u0C28\u0C2E\u0C38\u0C4D\u0C15\u0C3E\u0C30\u0C02|\u0C28\u0C2E\u0C38\u0C4D\u0C24\u0C47|\u0C28\u0C2E\u0C38\u0C4D\u0C15\u0C3E\u0C30\u0C2E\u0C02\u0C21\u0C3F|\u0C35\u0C02\u0C26\u0C28\u0C3E\u0C32\u0C41)",
    r"(?:\u0C26\u0C2F\u0C1A\u0C47\u0C38\u0C3F|\u0C26\u0C2F\u0C35\u0C41\u0C02\u0C1A\u0C3F)",
    r"(?:\u0C1A\u0C46\u0C2A\u0C4D\u0C2A\u0C02\u0C21\u0C3F|\u0C1A\u0C46\u0C2A\u0C4D\u0C2A\u0C17\u0C32\u0C30\u0C3E|\u0C1A\u0C47\u0C2F\u0C17\u0C32\u0C30\u0C3E|\u0C07\u0C35\u0C4D\u0C35\u0C17\u0C32\u0C30\u0C3E)",
    r"(?:\u0C17\u0C3E\u0C30\u0C41|\u0C05\u0C02\u0C21\u0C3F)",
    r"(?:\u0C27\u0C28\u0C4D\u0C2F\u0C35\u0C3E\u0C26\u0C3E\u0C32\u0C41)",
]

# Masked name phrases and name references to strip before matching
NAME_PHRASES = [
    r"\b(?:my\s+name\s+is\s+\[name\]|on\s+my\s+name|in\s+my\s+name|naa\s+peru\s+\[name\]|naa\s+peru\s+meeda|naa\s+peru\s+tho|\[name\]|\[masked\])\b",
    r"(?:\u0C28\u0C3E\s*\u0C2A\u0C47\u0C30\u0C41\s*\[name\]|\u0C28\u0C3E\s*\u0C2A\u0C47\u0C30\u0C41\s*\u0C2E\u0C40\u0C26|\u0C28\u0C3E\s*\u0C2A\u0C47\u0C30\u0C41\s*\u0C24\u0C4B)",
    r"\b(?:my\s+name\s+is|naa\s+peru|\u0C28\u0C3E\s*\u0C2A\u0C47\u0C30\u0C41)\b",
]

# Intent keyword lists (Telugu script, romanized Telugu, and English)
KEYWORDS = {
    "BOOK": [
        "book", "booking", "token", "appointment",
        "need a token", "want a token", "take a token", "give a token",
        "kavali", "kavalsi", "teesukovali", "ivvandi",
        "టోకెన్", "అపాయింట్మెంట్", "కావాలి", "బుక్", "తీసుకోవాలి", "ఇవ్వండి",
    ],
    "STATUS": [
        "status", "my token", "my number", "my turn", "when", "how many", "how long",
        "position", "queue", "token number", "token no", "token status", "eppudu", "entha", "ahead",
        "check token", "check my token", "naa token", "na token",
        "ఎప్పుడు", "ఎంతమంది", "నంబర్", "ఎంత", "నా టోకెన్", "టోకెన్ నంబర్", "స్టేటస్",
    ],
    "CANCEL": [
        "cancel", "cancelling", "cancelled", "delete", "remove",
        "raddu", "radhu",
        "రద్దు", "క్యాన్సిల్",
    ],
    "YES": [
        "yes", "yeah", "okay", "ok", "sure", "confirm", "confirmed", "yep",
        "avunu", "sare", "correct", "ha", "haa",
        "అవును", "సరే", "హా",
    ],
    "NO": [
        "no", "nope", "do not", "dont", "don't", "never",
        "vaddu", "kadu", "kaadu", "stop", "cheyyoddu", "cheyyaku",
        "వద్దు", "కాదు", "చేయొద్దు", "చేయవద్దు", "చేయకు",
    ],
    "DAY_TODAY": [
        "today", "now", "ivala", "ee roju", "eroju", "eeroju", "e roju",
        "ఈరోజు", "ఇవాళ", "ఈ రోజు",
    ],
    "DAY_TOMORROW": [
        "tomorrow", "repu", "raepu",
        "రేపు",
    ],
}


class ParseResult(NamedTuple):
    intent: str
    day: Optional[str]
    confidence: float = 1.0


def normalize_text(text: str) -> str:
    """
    Normalizes text:
    1. Redacts PII via privacy service.
    2. Removes polite words, greetings, and fillers.
    3. Removes masked name references.
    4. Cleans punctuation and maps common phonetic variants.
    """
    if not text:
        return ""

    # 1. Privacy masking
    masked = privacy.mask_text(text)

    # 2. Strip polite words & fillers
    for pattern in POLITE_PATTERNS:
        masked = re.sub(pattern, " ", masked, flags=re.IGNORECASE)

    # 3. Strip name phrases
    for pattern in NAME_PHRASES:
        masked = re.sub(pattern, " ", masked, flags=re.IGNORECASE)

    lowered = masked.lower()
    lowered = lowered.replace("'", "").replace("’", "").replace("`", "")

    # Remove punctuation preserving alphanumeric and Telugu script
    cleaned = re.sub(r"[^\w\s\u0C00-\u0C7F]", " ", lowered)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()

    # Map common phonetic variants
    variant_map = [
        (r"\bkaav+a+li\b", "kavali"),
        (r"\bkaavali\b", "kavali"),
        (r"\bkavaali\b", "kavali"),
        (r"\bkavli\b", "kavali"),
        (r"\braepu\b", "repu"),
        (r"\bradd*h*u\b", "raddu"),
        (r"\bradh+u\b", "raddu"),
        (r"\bcancle\b", "cancel"),
        (r"\btokn\b", "token"),
        (r"\bbok\b", "book"),
        (r"\bsttatus\b", "status"),
        (r"\btommorow\b", "tomorrow"),
        (r"\btomorow\b", "tomorrow"),
    ]
    for pattern, repl in variant_map:
        collapsed = re.sub(pattern, repl, collapsed)

    return collapsed


def _is_negated_cancel(text: str) -> bool:
    """Checks if cancellation is negated (e.g. 'do not cancel', 'token cancel vaddu')."""
    cancel_kw = r"(?:cancel|cancle|cancelling|raddu|radhu|\u0C30\u0C26\u0C4D\u0C26\u0C41|\u0C15\u0C4D\u0C2F\u0C3E\u0C28\u0C4D\u0C38\u0C3F\u0C32\u0C4D)"
    en_neg_terms = r"\b(?:do\s+not|dont|don\x27t|never|not)\b"
    all_neg_terms = (
        r"\b(?:do\s+not|dont|don\x27t|never|no|not|"
        r"vaddu|vaddhu|kaadu|kadu|cheyyoddu|cheyoddu|cheyyaku|cheyaku|oddu|valaddu)\b|"
        r"(?:\u0C35\u0C26\u0C4D\u0C26\u0C41|\u0C15\u0C3E\u0C26\u0C41|\u0C1A\u0C47\u0C2F\u0C4A\u0C26\u0C4D\u0C26\u0C41|\u0C1A\u0C47\u0C2F\u0C35\u0C26\u0C4D\u0C26\u0C41|\u0C1A\u0C47\u0C2F\u0C15\u0C41)"
    )
    before_pat = rf"(?:{en_neg_terms})(?:\s+\S+){{0,2}}\s+{cancel_kw}"
    after_pat = rf"{cancel_kw}(?:\s+\S+){{0,3}}\s+(?:{all_neg_terms})"
    return bool(re.search(before_pat, text, re.IGNORECASE) or re.search(after_pat, text, re.IGNORECASE))


def _match_keyword(kw: str, text: str, threshold: float = 85.0) -> tuple[bool, float]:
    """Checks if keyword matches in text using exact word boundary or sliding fuzzy window."""
    cleaned_kw = kw.lower().replace("'", "").replace("’", "").replace("`", "").strip()
    if not cleaned_kw:
        return False, 0.0

    # Native script: exact substring match
    if not cleaned_kw.isascii():
        if cleaned_kw in text:
            return True, 100.0
        return False, 0.0

    # Exact word-boundary match
    pattern = rf"\b{re.escape(cleaned_kw)}\b"
    if re.search(pattern, text):
        return True, 100.0

    words = text.split()
    if not words:
        return False, 0.0

    kw_words = cleaned_kw.split()
    kw_len = len(kw_words)
    best_score = 0.0

    if kw_len == 1:
        if len(cleaned_kw) >= 3:
            for w in words:
                if abs(len(w) - len(cleaned_kw)) <= 2:
                    score = float(fuzz.ratio(w, cleaned_kw))
                    if score > best_score:
                        best_score = score
    else:
        req_thresh = 95.0 if len(cleaned_kw) <= 10 else threshold
        min_win = max(1, kw_len - 1)
        max_win = min(len(words), kw_len + 1)
        for win_size in range(min_win, max_win + 1):
            for i in range(len(words) - win_size + 1):
                window = " ".join(words[i : i + win_size])
                score = float(fuzz.ratio(window, cleaned_kw))
                if score > best_score:
                    best_score = score

        if best_score >= req_thresh:
            return True, best_score
        return False, best_score

    if best_score >= threshold:
        return True, best_score

    return False, best_score


def _score_intent(norm: str, keywords: list[str], threshold: float = 85.0) -> tuple[int, float]:
    """Counts keyword hits and tracks maximum similarity score."""
    hits = 0
    max_score = 0.0
    for kw in keywords:
        matched, score = _match_keyword(kw, norm, threshold)
        if matched:
            hits += 1
            if score > max_score:
                max_score = score
    return hits, max_score


def _extract_day(norm: str) -> Optional[str]:
    """
    Extracts day: 'today', 'tomorrow', or None.
    'kal' is explicitly ignored as per specification.
    """
    # Remove 'kal' so it never matches
    filtered_norm = re.sub(r"\bkal\b", " ", norm)

    today_hits, today_score = _score_intent(filtered_norm, KEYWORDS["DAY_TODAY"], threshold=85.0)
    tomorrow_hits, tomorrow_score = _score_intent(filtered_norm, KEYWORDS["DAY_TOMORROW"], threshold=85.0)

    if today_hits > tomorrow_hits:
        return "today"
    if tomorrow_hits > today_hits:
        return "tomorrow"
    if today_hits > 0 and tomorrow_hits > 0:
        return "today" if today_score >= tomorrow_score else "tomorrow"
    return None


def _call_groq_fallback(text: str) -> ParseResult:
    """Optional LLM fallback via Groq if key exists and rules return UNKNOWN."""
    if not settings.GROQ_API_KEY:
        return ParseResult(intent="UNKNOWN", day=None, confidence=0.0)

    masked_text = privacy.mask_text(text)

    prompt = (
        "You are an NLU parser for a clinic token system in India. "
        "The user spoke Telugu, English, or Mix. "
        "Classify the text into: "
        "intent: one of ['BOOK', 'STATUS', 'CANCEL', 'YES', 'NO', 'UNKNOWN']. "
        "day: one of ['today', 'tomorrow', null]. "
        "Return ONLY a valid JSON object like: {\"intent\": \"BOOK\", \"day\": \"tomorrow\"}. "
        f"Input: \"{masked_text}\""
    )

    try:
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                intent = parsed.get("intent", "UNKNOWN").upper()
                day = parsed.get("day")
                if intent not in {"BOOK", "STATUS", "CANCEL", "YES", "NO", "UNKNOWN"}:
                    intent = "UNKNOWN"
                if day not in {"today", "tomorrow"}:
                    day = None
                return ParseResult(intent=intent, day=day, confidence=0.9)
    except Exception:
        pass

    return ParseResult(intent="UNKNOWN", day=None, confidence=0.0)


def parse(text: str, pending_confirm: bool = False) -> ParseResult:
    """
    Parses user input text with hardened, forgiving intent matching.
    - Filters greetings and polite words.
    - Redacts and ignores name phrases.
    - Handles negation ('do not cancel' does not cancel).
    - Checks status with token numbers ('token number seven') and 'my token'.
    - Handles day words (today, tomorrow, repu, ivala, ee roju; ignores 'kal').
    - If two conflicting actions appear (book and cancel), triggers CLARIFY.
    - Ties broken by CANCEL > STATUS > BOOK.
    - Confidence below 0.4 triggers say-again.
    """
    norm = normalize_text(text)
    if not norm:
        return ParseResult(intent="UNKNOWN", day=None, confidence=0.0)

    extracted_day = _extract_day(norm)

    # 1. Handle confirmation state precedence
    if pending_confirm:
        # Check explicit cancel negation during confirm: e.g. "don't cancel" -> NO
        if _is_negated_cancel(text):
            return ParseResult(intent="NO", day=extracted_day, confidence=0.95)

        yes_hits, yes_score = _score_intent(norm, KEYWORDS["YES"], threshold=85.0)
        no_hits, no_score = _score_intent(norm, KEYWORDS["NO"], threshold=85.0)

        if yes_hits > 0 and no_hits == 0:
            conf = round(min(1.0, (yes_score / 100.0) * (0.8 + 0.1 * min(yes_hits, 2))), 2)
            return ParseResult(intent="YES", day=extracted_day, confidence=conf)
        elif no_hits > 0 and yes_hits == 0:
            conf = round(min(1.0, (no_score / 100.0) * (0.8 + 0.1 * min(no_hits, 2))), 2)
            return ParseResult(intent="NO", day=extracted_day, confidence=conf)
        elif yes_hits > 0 and no_hits > 0:
            if no_hits >= yes_hits:
                conf = round(min(1.0, (no_score / 100.0) * 0.8), 2)
                return ParseResult(intent="NO", day=extracted_day, confidence=conf)
            else:
                conf = round(min(1.0, (yes_score / 100.0) * 0.8), 2)
                return ParseResult(intent="YES", day=extracted_day, confidence=conf)

    # 2. Check for negation on non-pending turns
    cancel_negated = _is_negated_cancel(text)
    if cancel_negated:
        return ParseResult(intent="NO", day=None, confidence=0.95)

    # 3. Check for conflicting actions (both book and cancel actions appear)
    has_book_action = bool(re.search(r"\b(?:book|booking|\u0C2C\u0C41\u0C15\u0C4D)\b", norm, re.IGNORECASE))
    has_cancel_action = bool(re.search(r"\b(?:cancel|cancle|cancelling|raddu|radhu|\u0C30\u0C26\u0C4D\u0C26\u0C41|\u0C15\u0C4D\u0C2F\u0C3E\u0C28\u0C4D\u0C38\u0C3F\u0C32\u0C4D)\b", norm, re.IGNORECASE))
    if has_book_action and has_cancel_action:
        return ParseResult(intent="CLARIFY", day=extracted_day, confidence=0.35)

    # 4. Score keywords per intent
    intent_order = ["CANCEL", "STATUS", "BOOK", "YES", "NO"]
    intent_scores: dict[str, tuple[int, float]] = {}

    for intent_name in intent_order:
        hits, max_score = _score_intent(norm, KEYWORDS[intent_name], threshold=85.0)
        intent_scores[intent_name] = (hits, max_score)

    # If cancel action is present, noun keywords 'token' or 'appointment' belong to cancellation
    if intent_scores["CANCEL"][0] > 0 and not has_book_action:
        intent_scores["BOOK"] = (0, 0.0)

    # Boost STATUS if specific status patterns appear (e.g. 'token number seven', 'my token', 'token 7')
    status_number_match = re.search(
        r"\b(?:token\s+(?:number\s+|no\s+|\#\s*)?(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)|my\s+token|naa\s+token|na\s+token|\u0C28\u0C3E\s*\u0C1F\u0C4B\u0C15\u0C46\u0C28\u0C4D)\b",
        norm,
        re.IGNORECASE,
    )
    if status_number_match and not has_book_action and intent_scores["CANCEL"][0] == 0:
        cur_hits, cur_score = intent_scores["STATUS"]
        intent_scores["STATUS"] = (cur_hits + 2, max(cur_score, 100.0))

    total_hits = sum(h for h, _ in intent_scores.values())
    max_hits = max(h for h, _ in intent_scores.values())

    if max_hits == 0:
        fallback = _call_groq_fallback(norm)
        if fallback.intent != "UNKNOWN":
            return fallback
        return ParseResult(intent="UNKNOWN", day=None, confidence=0.0)

    # Tie-breaking priority: CANCEL > STATUS > BOOK > YES > NO
    candidates = [name for name in intent_order if intent_scores[name][0] == max_hits]
    winning_intent = candidates[0]
    win_hits, win_max_score = intent_scores[winning_intent]

    # Calculate confidence between 0 and 1
    r = win_max_score / 100.0
    base_conf = (0.75 + 0.10 * min(win_hits, 3)) * r
    conflict_hits = total_hits - win_hits
    conflict_penalty = 0.15 * min(conflict_hits, 2)
    confidence = round(max(0.0, min(1.0, base_conf * (1.0 - conflict_penalty))), 2)

    # Low confidence (< 0.4) gives UNKNOWN
    if confidence < 0.4:
        fallback = _call_groq_fallback(norm)
        if fallback.intent != "UNKNOWN":
            return fallback
        return ParseResult(intent="UNKNOWN", day=None, confidence=confidence)

    # BOOK with no day defaults to tomorrow
    day = extracted_day
    if winning_intent == "BOOK" and day is None:
        day = "tomorrow"

    return ParseResult(intent=winning_intent, day=day, confidence=confidence)

"""Telugu Reply Review Pipeline Service (Phase P2-6).

Centralizes all Telugu strings across the application:
- Spoken reply templates (replies.py)
- Spoken number words (0 to 20, and 30, 40, 50 as examples)
- Error catalog messages & suggested actions (shared/error_catalog.json)
- UI strings shown on the patient page
- Cached phrase mappings

Provides export to docs/telugu_review.csv and import with style validation,
code updating, reviewed.json tracking, and safe --confirm guarded audio regeneration.
"""

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Base repository root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = _REPO_ROOT / "docs"
DOCS_CSV_PATH = DOCS_DIR / "telugu_review.csv"
DOCS_REVIEWED_JSON = DOCS_DIR / "reviewed.json"
SHARED_ERROR_CATALOG_PATH = _REPO_ROOT / "shared" / "error_catalog.json"
REPLIES_PY_PATH = _REPO_ROOT / "backend" / "app" / "services" / "replies.py"
NUMBER_WORDS_PY_PATH = _REPO_ROOT / "backend" / "app" / "services" / "number_words.py"


@dataclass
class TeluguReviewItem:
    key: str
    telugu_text: str
    english_meaning: str
    cached_phrase_key: str  # Non-empty if backed by a pre-synthesized audio cache file
    category: str           # "reply_template", "number_word", "credit_limit", "error_catalog", "ui_string"
    corrected_text: str = ""
    comment: str = ""
    approved: str = ""


# Canonical catalog of all Telugu strings in VoiceQueue
CANONICAL_TELUGU_ITEMS: List[TeluguReviewItem] = [
    # 1. Spoken Reply Templates (backend/app/services/replies.py)
    TeluguReviewItem(
        key="greeting_te",
        telugu_text="నమస్కారం, డెమో క్లినిక్ వాయిస్ క్యూకి స్వాగతం. మీరు టోకెన్ బుక్ చేయవచ్చు, స్టేటస్ తెలుసుకోవచ్చు లేదా రద్దు చేయవచ్చు.",
        english_meaning="Hello, welcome to Demo Clinic voice queue. You can book a token, check your status, or cancel your appointment.",
        cached_phrase_key="greeting_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="say_again_te",
        telugu_text="క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి.",
        english_meaning="Sorry, I could not hear you clearly. Please say that again.",
        cached_phrase_key="say_again_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="booked_today_te",
        telugu_text="మీ టోకెన్ ఈరోజు నంబర్ {number} బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.",
        english_meaning="Your token for today is number {number}. Please come to the clinic on time.",
        cached_phrase_key="",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="booked_tomorrow_te",
        telugu_text="మీ టోకెన్ రేపు నంబర్ {number} బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.",
        english_meaning="Your token for tomorrow is number {number}. Please come to the clinic on time.",
        cached_phrase_key="",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="status_now_te",
        telugu_text="మీ టోకెన్ నంబర్ {number}. ఇప్పుడు మీ వంతు వచ్చింది, దయచేసి డాక్టర్ గదిలోకి వెళ్లండి.",
        english_meaning="Your token number is {number}. It is your turn now, please proceed to the doctor.",
        cached_phrase_key="",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="status_waiting_te",
        telugu_text="మీ టోకెన్ నంబర్ {number}. ప్రస్తుతం మీ ముందు {ahead} మంది వేచి ఉన్నారు.",
        english_meaning="Your token number is {number}. There are {ahead} patients waiting ahead of you.",
        cached_phrase_key="",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="cancel_confirm_te",
        telugu_text="మీరు టోకెన్ నంబర్ {number} రద్దు చేయాలనుకుంటున్నారా? అవును లేదా వద్దు అని చెప్పండి.",
        english_meaning="Are you sure you want to cancel token number {number}? Please say yes or no.",
        cached_phrase_key="",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="cancelled_te",
        telugu_text="మీ టోకెన్ విజయవంతంగా రద్దు చేయబడింది.",
        english_meaning="Your token has been cancelled successfully.",
        cached_phrase_key="cancelled_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="cancel_aborted_te",
        telugu_text="టోకెన్ రద్దు ప్రక్రియ ఆపివేయబడింది.",
        english_meaning="Token cancellation was cancelled.",
        cached_phrase_key="cancel_aborted_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="no_token_te",
        telugu_text="మీ పేరుతో ఎటువంటి యాక్టివ్ టోకెన్ కనుగొనబడలేదు.",
        english_meaning="No active token was found for you.",
        cached_phrase_key="no_token_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="unknown_te",
        telugu_text="క్షమించండి, మీ మాట అర్థం కాలేదు. దయచేసి టోకెన్ బుక్ చేయండి, స్టేటస్ లేదా క్యాన్సిల్ అని చెప్పండి.",
        english_meaning="Sorry, I did not understand. Please say book token, status, or cancel.",
        cached_phrase_key="unknown_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="service_paused_te",
        telugu_text="సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి.",
        english_meaning="The service is currently paused. Please try again later.",
        cached_phrase_key="service_paused_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="too_quiet_te",
        telugu_text="మీ మాట చాలా తక్కువగా వినిపించింది. దయచేసి కొంచెం గట్టిగా మాట్లాడండి.",
        english_meaning="Your voice is too quiet. Please speak louder or bring the microphone closer.",
        cached_phrase_key="too_quiet_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="no_speech_te",
        telugu_text="ఎటువంటి మాటలు వినిపించలేదు. దయచేసి మైక్రోఫోన్ దగ్గరగా మళ్లీ మాట్లాడండి.",
        english_meaning="No speech was detected. Please speak clearly into the microphone.",
        cached_phrase_key="no_speech_te",
        category="reply_template",
    ),
    TeluguReviewItem(
        key="clarify_book_or_cancel_te",
        telugu_text="మీరు టోకెన్ బుక్ చేయాలనుకుంటున్నారా లేదా రద్దు చేయాలనుకుంటున్నారా? దయచేసి చెప్పండి.",
        english_meaning="Do you want to book a token or cancel a token? Please say clearly.",
        cached_phrase_key="",
        category="reply_template",
    ),

    # 2. Number Words (0 to 20, and 30, 40, 50 as examples)
    TeluguReviewItem(key="num_0_te", telugu_text="సున్నా", english_meaning="zero (0)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_1_te", telugu_text="ఒకటి", english_meaning="one (1)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_2_te", telugu_text="రెండు", english_meaning="two (2)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_3_te", telugu_text="మూడు", english_meaning="three (3)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_4_te", telugu_text="నాలుగు", english_meaning="four (4)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_5_te", telugu_text="ఐదు", english_meaning="five (5)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_6_te", telugu_text="ఆరు", english_meaning="six (6)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_7_te", telugu_text="ఏడు", english_meaning="seven (7)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_8_te", telugu_text="ఎనిమిది", english_meaning="eight (8)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_9_te", telugu_text="తొమ్మిది", english_meaning="nine (9)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_10_te", telugu_text="పది", english_meaning="ten (10)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_11_te", telugu_text="పదకొండు", english_meaning="eleven (11)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_12_te", telugu_text="పన్నెండు", english_meaning="twelve (12)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_13_te", telugu_text="పదమూడు", english_meaning="thirteen (13)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_14_te", telugu_text="పద్నాలుగు", english_meaning="fourteen (14)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_15_te", telugu_text="పదిహేను", english_meaning="fifteen (15)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_16_te", telugu_text="పదహారు", english_meaning="sixteen (16)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_17_te", telugu_text="పదిహేడు", english_meaning="seventeen (17)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_18_te", telugu_text="పద్దెనిమిది", english_meaning="eighteen (18)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_19_te", telugu_text="పందొమ్మిది", english_meaning="nineteen (19)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_20_te", telugu_text="ఇరవై", english_meaning="twenty (20)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_30_te", telugu_text="ముప్పై", english_meaning="thirty (30)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_40_te", telugu_text="నలభై", english_meaning="forty (40)", cached_phrase_key="", category="number_word"),
    TeluguReviewItem(key="num_50_te", telugu_text="యాభై", english_meaning="fifty (50)", cached_phrase_key="", category="number_word"),

    # 3. Credit Protection & Demo Limit (P1-6)
    TeluguReviewItem(
        key="demo_limit_te",
        telugu_text="ప్రస్తుతానికి వాయిస్ డెమో పరిమితి పూర్తయింది. దయచేసి డెమో వీడియో చూడండి లేదా టైప్ చేసి ప్రయత్నించండి.",
        english_meaning="Voice demo limit reached for now. Please watch the demo video or try typing.",
        cached_phrase_key="",
        category="credit_limit",
    ),

    # 4. Error Catalog Messages & Actions (shared/error_catalog.json)
    TeluguReviewItem(key="error_mic_denied_te", telugu_text="మైక్రోఫోన్ అనుమతి నిరాకరించబడింది.", english_meaning="Microphone access was denied.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_mic_denied_action_te", telugu_text="టైప్ చేయండి", english_meaning="Type instead", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_too_short_te", telugu_text="ఆడియో చాలా తక్కువగా ఉంది, దయచేసి కొంచెం సేపు మాట్లాడండి.", english_meaning="Recording was too short, please speak longer.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_too_short_action_te", telugu_text="మళ్లీ ప్రయత్నించండి", english_meaning="Try again", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_too_quiet_te", telugu_text="మీ మాట చాలా తక్కువగా వినిపించింది. దయచేసి కొంచెం గట్టిగా మాట్లాడండి.", english_meaning="Your voice was too quiet. Please speak louder.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_too_loud_te", telugu_text="ధ్వని చాలా ఎక్కువగా లేదా అస్పష్టంగా ఉంది.", english_meaning="Audio was too loud or distorted.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_no_speech_te", telugu_text="ఎటువంటి మాటలు వినిపించలేదు. దయచేసి మైక్రోఫోన్ దగ్గరగా మళ్లీ మాట్లాడండి.", english_meaning="No speech was detected. Please speak clearly.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_unclear_speech_te", telugu_text="మీ మాట స్పష్టంగా అర్థం కాలేదు.", english_meaning="Could not understand your speech clearly.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_gnani_key_missing_te", telugu_text="సర్వర్ వాయిస్ సర్వీస్ కీ అమర్చబడలేదు.", english_meaning="Voice service key is not configured.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_voice_invalid_te", telugu_text="అమర్చిన వాయిస్ సరైనది కాదు.", english_meaning="Configured voice name is invalid.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_gnani_error_te", telugu_text="వాయిస్ సర్వీస్ తాత్కాలికంగా ఆగిపోయింది.", english_meaning="Voice service encountered a temporary error.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_credit_limit_te", telugu_text="వాయిస్ క్రెడిట్ పరిమితి ముగిసింది.", english_meaning="Voice credit limit reached.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_demo_limit_te", telugu_text="వాయిస్ డెమో పరిమితి పూర్తయింది. దయచేసి టైప్ చేయండి లేదా డెమో వీడియో చూడండి.", english_meaning="Voice demo limit reached. Please type or watch demo video.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_network_error_te", telugu_text="సర్వర్‌తో కనెక్ట్ కాలేకపోయాము. దయచేసి నెట్‌వర్క్ తనిఖీ చేయండి.", english_meaning="Could not connect to server. Please check network.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_audio_unavailable_te", telugu_text="ఈ ప్రత్యుత్తరానికి ఆడియో అందుబాటులో లేదు.", english_meaning="Audio reply is unavailable for this message.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_token_not_found_te", telugu_text="మీ పేరుతో ఎటువంటి యాక్టివ్ టోకెన్ కనుగొనబడలేదు.", english_meaning="No active token was found for you.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_already_cancelled_te", telugu_text="ఈ టోకెన్ ఇప్పటికే రద్దు చేయబడింది.", english_meaning="This token has already been cancelled.", cached_phrase_key="", category="error_catalog"),
    TeluguReviewItem(key="error_server_error_te", telugu_text="సర్వర్‌లో తాత్కాలిక లోపం ఏర్పడింది.", english_meaning="A temporary server error occurred.", cached_phrase_key="", category="error_catalog"),

    # 5. UI Strings on Patient Page
    TeluguReviewItem(
        key="ui_clinic_tagline_te",
        telugu_text="క్లినిక్ టోకెన్ బుక్ చేయడానికి తెలుగు లేదా English లో మాట్లాడండి.",
        english_meaning="Speak in Telugu or English to book a clinic token.",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_try_chip_book_te",
        telugu_text="నాకు రేపు టోకెన్ కావాలి",
        english_meaning="I need a token for tomorrow",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_try_chip_status_te",
        telugu_text="నా టోకెన్ స్టేటస్ ఏమిటి",
        english_meaning="What is my token status",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_try_chip_cancel_te",
        telugu_text="నా టోకెన్ రద్దు చేయండి",
        english_meaning="Cancel my token",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_mic_hint_te",
        telugu_text="మాట్లాడటానికి SPACE నొక్కి పట్టుకోండి. మైక్రోఫోన్ ఉన్న ఇయర్‌ఫోన్లు బాగా పనిచేస్తాయి.",
        english_meaning="Hold SPACE to speak. Earphones with a microphone work best.",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_first_visit_prompt_te",
        telugu_text="ధ్వని వినడానికి స్క్రీన్‌పై ఎక్కడైనా ఒకసారి క్లిక్ చేయండి, తర్వాత SPACE పట్టుకోండి.",
        english_meaning="Click once anywhere to allow sound, then hold SPACE.",
        cached_phrase_key="",
        category="ui_string",
    ),
    TeluguReviewItem(
        key="ui_empty_token_te",
        telugu_text="ఇంకా టోకెన్ లేదు. ఇలా చెప్పి చూడండి: రేపు టోకెన్ కావాలి",
        english_meaning="No token yet. Try saying: I need a token for tomorrow",
        cached_phrase_key="",
        category="ui_string",
    ),
]


def validate_style_rules(text: str, key: str) -> List[str]:
    """Validates Telugu style rules:
    - short sentences
    - polite but simple words
    - common spoken Telugu (not heavy formal Telugu)
    - English words allowed for token, clinic, doctor
    - numbers always spoken as words (no raw ASCII digits 0-9 in spoken templates).
    """
    warnings: List[str] = []
    # Check for raw numbers in spoken templates (except template placeholders like {number})
    cleaned_placeholders = re.sub(r"\{(number|ahead)\}", "", text)
    if re.search(r"\b\d+\b", cleaned_placeholders):
        warnings.append(f"[{key}] Spoken string contains raw digits. Numbers must always be words.")

    # Check for heavy formal words that should be replaced with common spoken Telugu
    formal_words = {
        "విరమించబడినది": "రద్దు చేయబడింది",
        "అంతరాయము": "ఆగిపోయింది",
        "కనుగొనబడలేదు": "లేదు",
    }
    for formal, spoken in formal_words.items():
        if formal in text:
            warnings.append(f"[{key}] Found formal word '{formal}'. Prefer spoken '{spoken}'.")

    return warnings


def export_review_csv(output_path: Path = DOCS_CSV_PATH) -> int:
    """Exports all canonical Telugu strings to docs/telugu_review.csv.
    Preserves existing reviewer columns (corrected_text, comment, approved) if file already exists.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing review entries if file exists
    existing_reviews: Dict[str, Dict[str, str]] = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    k = (row.get("key") or "").strip()
                    if k:
                        existing_reviews[k] = {
                            "corrected_text": row.get("corrected_text", "") or "",
                            "comment": row.get("comment", "") or "",
                            "approved": row.get("approved", "") or "",
                        }
        except Exception as e:
            print(f"[Warning] Could not parse existing CSV: {e}")

    fieldnames = [
        "key",
        "telugu_text",
        "english_meaning",
        "cached_phrase_key",
        "category",
        "corrected_text",
        "comment",
        "approved",
    ]

    count = 0
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in CANONICAL_TELUGU_ITEMS:
            prev = existing_reviews.get(item.key, {})
            writer.writerow(
                {
                    "key": item.key,
                    "telugu_text": item.telugu_text,
                    "english_meaning": item.english_meaning,
                    "cached_phrase_key": item.cached_phrase_key,
                    "category": item.category,
                    "corrected_text": prev.get("corrected_text", item.corrected_text),
                    "comment": prev.get("comment", item.comment),
                    "approved": prev.get("approved", item.approved),
                }
            )
            count += 1

    return count


def load_review_csv(csv_path: Path = DOCS_CSV_PATH) -> List[Dict[str, str]]:
    """Loads docs/telugu_review.csv into row dicts."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Review CSV file not found at: {csv_path}")

    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def update_code_with_reviews(reviews_by_key: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Updates number_words.py, replies.py, error_catalog.json, and reviewed.json with reviewed texts."""
    updated_files = []

    # 1. Update number_words.py if any numbers changed
    try:
        from backend.app.services import number_words
        num_changed = False
        new_0_to_19 = list(number_words.TELUGU_0_TO_19)
        new_tens = dict(number_words.TELUGU_TENS)

        for i in range(20):
            k = f"num_{i}_te"
            if k in reviews_by_key:
                val = reviews_by_key[k]["text"]
                if val != new_0_to_19[i]:
                    new_0_to_19[i] = val
                    num_changed = True

        for t in (20, 30, 40, 50):
            k = f"num_{t}_te"
            if k in reviews_by_key:
                val = reviews_by_key[k]["text"]
                if val != new_tens.get(t):
                    new_tens[t] = val
                    num_changed = True

        if num_changed and NUMBER_WORDS_PY_PATH.exists():
            content = NUMBER_WORDS_PY_PATH.read_text(encoding="utf-8")
            # Format list of 0-19
            formatted_0_19 = '[\n    "' + '", "'.join(new_0_to_19[:5]) + '",\n    "' + '", "'.join(new_0_to_19[5:10]) + '",\n    "' + '", "'.join(new_0_to_19[10:15]) + '",\n    "' + '", "'.join(new_0_to_19[15:20]) + '",\n]'
            content = re.sub(r"TELUGU_0_TO_19\s*=\s*\[[\s\S]*?\]", f"TELUGU_0_TO_19 = {formatted_0_19}", content)
            
            # Format tens dict
            tens_str = "{\n" + "\n".join(f'    {k}: "{v}",' for k, v in new_tens.items()) + "\n}"
            content = re.sub(r"TELUGU_TENS\s*=\s*\{[\s\S]*?\}", f"TELUGU_TENS = {tens_str}", content)
            
            NUMBER_WORDS_PY_PATH.write_text(content, encoding="utf-8")
            updated_files.append("backend/app/services/number_words.py")
    except Exception as e:
        print(f"[Warning] Failed to update number_words.py: {e}")

    # 2. Update shared/error_catalog.json if any error messages changed
    try:
        if SHARED_ERROR_CATALOG_PATH.exists():
            with open(SHARED_ERROR_CATALOG_PATH, "r", encoding="utf-8") as f:
                cat = json.load(f)
            err_changed = False
            for k, rev in reviews_by_key.items():
                if k.startswith("error_"):
                    # e.g. error_mic_denied_te or error_mic_denied_action_te
                    parts = k.split("_")
                    if "action" in parts:
                        code = "_".join(parts[1:-2]) if len(parts) > 3 else parts[1]
                        if code in cat and "suggested_action" in cat[code]:
                            if cat[code]["suggested_action"].get("te") != rev["text"]:
                                cat[code]["suggested_action"]["te"] = rev["text"]
                                err_changed = True
                    else:
                        code = "_".join(parts[1:-1])
                        if code in cat and "message" in cat[code]:
                            if cat[code]["message"].get("te") != rev["text"]:
                                cat[code]["message"]["te"] = rev["text"]
                                err_changed = True

            if err_changed:
                with open(SHARED_ERROR_CATALOG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cat, f, ensure_ascii=False, indent=2)
                updated_files.append("shared/error_catalog.json")
    except Exception as e:
        print(f"[Warning] Failed to update shared/error_catalog.json: {e}")

    # 3. Write docs/reviewed.json
    try:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        canonical_keys = {item.key for item in CANONICAL_TELUGU_ITEMS}
        reviewed_keys_map = {}
        for k in canonical_keys:
            if k in reviews_by_key and reviews_by_key[k]["approved"]:
                reviewed_keys_map[k] = {
                    "text": reviews_by_key[k]["text"],
                    "approved": True,
                    "comment": reviews_by_key[k].get("comment", ""),
                }

        all_covered = canonical_keys.issubset(set(reviewed_keys_map.keys()))
        reviewed_json_data = {
            "all_reviewed": bool(all_covered),
            "reviewed_by_native_speaker": bool(all_covered),
            "total_strings": len(CANONICAL_TELUGU_ITEMS),
            "reviewed_count": len(reviewed_keys_map),
            "reviewed_keys": reviewed_keys_map,
        }
        with open(DOCS_REVIEWED_JSON, "w", encoding="utf-8") as f:
            json.dump(reviewed_json_data, f, ensure_ascii=False, indent=2)
        updated_files.append("docs/reviewed.json")
    except Exception as e:
        print(f"[Warning] Failed to write reviewed.json: {e}")

    return {
        "updated_files": updated_files,
        "all_reviewed": bool(all_covered),
        "reviewed_count": len(reviewed_keys_map),
        "total_strings": len(CANONICAL_TELUGU_ITEMS),
    }


def get_review_status() -> Dict[str, Any]:
    """Returns review status based on docs/reviewed.json and canonical strings."""
    if not DOCS_REVIEWED_JSON.exists():
        return {
            "all_reviewed": False,
            "reviewed_by_native_speaker": False,
            "total_strings": len(CANONICAL_TELUGU_ITEMS),
            "reviewed_count": 0,
            "missing_keys": [item.key for item in CANONICAL_TELUGU_ITEMS],
        }

    try:
        with open(DOCS_REVIEWED_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        reviewed_keys = data.get("reviewed_keys", {})
        canonical_keys = {item.key for item in CANONICAL_TELUGU_ITEMS}
        covered_keys = {k for k, v in reviewed_keys.items() if v.get("approved")}

        all_covered = canonical_keys.issubset(covered_keys) and len(covered_keys) >= len(canonical_keys)
        return {
            "all_reviewed": bool(all_covered),
            "reviewed_by_native_speaker": bool(all_covered),
            "total_strings": len(CANONICAL_TELUGU_ITEMS),
            "reviewed_count": len(covered_keys),
            "missing_keys": sorted(list(canonical_keys - covered_keys)),
        }
    except Exception as e:
        return {
            "all_reviewed": False,
            "reviewed_by_native_speaker": False,
            "total_strings": len(CANONICAL_TELUGU_ITEMS),
            "reviewed_count": 0,
            "error": str(e),
        }

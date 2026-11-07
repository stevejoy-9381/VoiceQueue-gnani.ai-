"""Bilingual reply templates (Telugu and English) with spoken number conversion and caching keys."""

from typing import Optional, Tuple
from backend.app.services.number_words import to_words


def _lang_prefix(lang: str) -> str:
    return "te" if (lang or "").startswith("te") else "en"


def greeting(lang: str = "te-IN") -> Tuple[str, str]:
    """Greeting prompt introducing the clinic queue voice assistant."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "నమస్కారం, డెమో క్లినిక్ వాయిస్ క్యూకి స్వాగతం. మీరు టోకెన్ బుక్ చేయవచ్చు, స్టేటస్ తెలుసుకోవచ్చు లేదా రద్దు చేయవచ్చు."
    else:
        text = "Hello, welcome to Demo Clinic voice queue. You can book a token, check your status, or cancel your appointment."
    return text, f"greeting_{lp}"


def say_again(lang: str = "te-IN") -> Tuple[str, str]:
    """Prompt asking user to repeat their speech when unclear or empty."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి."
    else:
        text = "Sorry, I could not hear you clearly. Please say that again."
    return text, f"say_again_{lp}"


def ask_day(lang: str = "te-IN") -> Tuple[str, str]:
    """Prompt asking patient to specify today or tomorrow when no day was mentioned."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "ఈరోజా లేదా రేపా?"
    else:
        text = "Today or tomorrow?"
    return text, f"ask_day_{lp}"


def booked(number: int, day: str, lang: str = "te-IN") -> Tuple[str, Optional[str]]:
    """Reply for successfully booked token. Contains number -> cache_key is None."""
    num_word = to_words(number, lang)
    if (lang or "").startswith("te"):
        day_str = "ఈరోజు" if day == "today" else "రేపు"
        text = f"మీ టోకెన్ {day_str} నంబర్ {num_word} బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి."
    else:
        day_str = "today" if day == "today" else "tomorrow"
        text = f"Your token for {day_str} is number {num_word}. Please come to the clinic on time."
    return text, None


def status(number: int, ahead: int, lang: str = "te-IN") -> Tuple[str, Optional[str]]:
    """Reply for queue position query. Contains number -> cache_key is None."""
    num_word = to_words(number, lang)
    ahead_word = to_words(ahead, lang)

    if (lang or "").startswith("te"):
        if ahead == 0:
            text = f"మీ టోకెన్ నంబర్ {num_word}. ఇప్పుడు మీ వంతు వచ్చింది, దయచేసి డాక్టర్ గదిలోకి వెళ్లండి."
        else:
            text = f"మీ టోకెన్ నంబర్ {num_word}. ప్రస్తుతం మీ ముందు {ahead_word} మంది వేచి ఉన్నారు."
    else:
        if ahead == 0:
            text = f"Your token number is {num_word}. It is your turn now, please proceed to the doctor."
        else:
            text = f"Your token number is {num_word}. There are {ahead_word} patients waiting ahead of you."
    return text, None


def cancel_confirm(number: int, lang: str = "te-IN") -> Tuple[str, Optional[str]]:
    """Confirmation prompt before cancellation. Contains number -> cache_key is None."""
    num_word = to_words(number, lang)
    if (lang or "").startswith("te"):
        text = f"మీరు టోకెన్ నంబర్ {num_word} రద్దు చేయాలనుకుంటున్నారా? అవును లేదా వద్దు అని చెప్పండి."
    else:
        text = f"Are you sure you want to cancel token number {num_word}? Please say yes or no."
    return text, None


def cancelled(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when token is cancelled. Fixed phrase -> returns cache_key."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "మీ టోకెన్ విజయవంతంగా రద్దు చేయబడింది."
    else:
        text = "Your token has been cancelled successfully."
    return text, f"cancelled_{lp}"


def cancel_aborted(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when token cancellation is aborted by user."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "టోకెన్ రద్దు ప్రక్రియ ఆపివేయబడింది."
    else:
        text = "Token cancellation was cancelled."
    return text, f"cancel_aborted_{lp}"


def no_token(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when no active token is found. Fixed phrase -> returns cache_key."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "మీ పేరుతో ఎటువంటి యాక్టివ్ టోకెన్ కనుగొనబడలేదు."
    else:
        text = "No active token was found for you."
    return text, f"no_token_{lp}"


def unknown(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when request could not be recognized. Fixed phrase -> returns cache_key."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "క్షమించండి, మీ మాట అర్థం కాలేదు. దయచేసి టోకెన్ బుక్ చేయండి, స్టేటస్ లేదా క్యాన్సిల్ అని చెప్పండి."
    else:
        text = "Sorry, I did not understand. Please say book token, status, or cancel."
    return text, f"unknown_{lp}"


def service_paused(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when clinic queue service is paused. Fixed phrase -> returns cache_key."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి."
    else:
        text = "The service is currently paused. Please try again later."
    return text, f"service_paused_{lp}"


def too_quiet(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when audio is too quiet."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "మీ మాట చాలా తక్కువగా వినిపించింది. దయచేసి కొంచెం గట్టిగా మాట్లాడండి."
    else:
        text = "Your voice is too quiet. Please speak louder or bring the microphone closer."
    return text, f"too_quiet_{lp}"


def no_speech(lang: str = "te-IN") -> Tuple[str, str]:
    """Reply when no speech detected."""
    lp = _lang_prefix(lang)
    if lp == "te":
        text = "ఎటువంటి మాటలు వినిపించలేదు. దయచేసి మైక్రోఫోన్ దగ్గరగా మళ్లీ మాట్లాడండి."
    else:
        text = "No speech was detected. Please speak clearly into the microphone."
    return text, f"no_speech_{lp}"


# Registry of all fixed phrase generators for cache building
FIXED_PHRASE_GENERATORS = {
    "greeting": greeting,
    "say_again": say_again,
    "ask_day": ask_day,
    "cancelled": cancelled,
    "no_token": no_token,
    "unknown": unknown,
    "service_paused": service_paused,
    "cancel_aborted": cancel_aborted,
    "too_quiet": too_quiet,
    "no_speech": no_speech,
}

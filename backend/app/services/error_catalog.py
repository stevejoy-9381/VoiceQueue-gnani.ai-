"""Error Message Catalog (Phase P1-9).

Provides bilingual friendly messages, suggested actions, and error mappings
so that no patient ever sees raw JSON, stack traces, or technical error codes.
Loads from shared/error_catalog.json to keep backend and frontend in sync.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Locate shared/error_catalog.json
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CATALOG_PATH = _BASE_DIR / "shared" / "error_catalog.json"

EXPECTED_ERROR_CODES: List[str] = [
    "mic_denied",
    "too_short",
    "too_quiet",
    "too_loud",
    "no_speech",
    "unclear_speech",
    "gnani_key_missing",
    "voice_invalid",
    "gnani_error",
    "credit_limit",
    "demo_limit",
    "network_error",
    "audio_unavailable",
    "token_not_found",
    "already_cancelled",
    "server_error",
]


def load_catalog() -> Dict[str, Any]:
    """Loads the canonical error catalog from shared/error_catalog.json."""
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


ERROR_CATALOG = load_catalog()


def normalize_language(lang: str) -> str:
    """Normalizes language code to 'te' or 'en'."""
    if not lang:
        return "te"
    l = lang.lower().strip()
    if l.startswith("te"):
        return "te"
    return "en"


def get_error(code: str, lang: str = "te") -> Dict[str, Any]:
    """
    Retrieves the error entry for a given error code and language.
    Falls back to 'server_error' if code is unknown.
    """
    entry = ERROR_CATALOG.get(code)
    if not entry:
        entry = ERROR_CATALOG.get("server_error", {})

    target_lang = normalize_language(lang)
    msg_dict = entry.get("message", {})
    action_dict = entry.get("suggested_action", {})

    message = msg_dict.get(target_lang) or msg_dict.get("en") or "An error occurred."
    suggested_action = action_dict.get(target_lang) or action_dict.get("en") or "Try again"
    action_type = entry.get("action_type", "try_again")

    return {
        "code": code,
        "message": message,
        "suggested_action": suggested_action,
        "action_type": action_type,
    }


def get_error_message(code: str, lang: str = "te") -> str:
    """Returns the user-facing localized message for an error code."""
    return get_error(code, lang)["message"]


def get_error_action(code: str, lang: str = "te") -> str:
    """Returns the user-facing localized suggested action for an error code."""
    return get_error(code, lang)["suggested_action"]


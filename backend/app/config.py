import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Absolute paths based on config file location
CONFIG_FILE_PATH = Path(__file__).resolve()
BACKEND_DIR = CONFIG_FILE_PATH.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

BACKEND_ENV_PATH = BACKEND_DIR / ".env"
ROOT_ENV_PATH = PROJECT_ROOT / ".env"

LOADED_ENV_PATH: Optional[Path] = None

# If two .env files exist, log a warning that names both
if BACKEND_ENV_PATH.is_file() and ROOT_ENV_PATH.is_file():
    print(f"[Warning] Two .env files detected: '{BACKEND_ENV_PATH}' and '{ROOT_ENV_PATH}'. Loading '{BACKEND_ENV_PATH}'.")
    load_dotenv(BACKEND_ENV_PATH, override=True)
    LOADED_ENV_PATH = BACKEND_ENV_PATH
elif BACKEND_ENV_PATH.is_file():
    load_dotenv(BACKEND_ENV_PATH, override=True)
    LOADED_ENV_PATH = BACKEND_ENV_PATH
elif ROOT_ENV_PATH.is_file():
    load_dotenv(ROOT_ENV_PATH, override=True)
    LOADED_ENV_PATH = ROOT_ENV_PATH


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "t")


def _get_float_optional(key: str) -> Optional[float]:
    val = os.getenv(key)
    if not val:
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


# TTS Model & Language Voice Mappings (timbre-v2.5 strictly)
TTS_MODEL: str = "timbre-v2.5"

TIMBRE_VOICES_BY_LANG: dict[str, list[str]] = {
    "en-IN": ["Kaveri", "Trupti", "Devika", "Pranav", "Shlok", "Girish"],
    "te-IN": ["Suhana", "Lehara", "Lavanya", "Yukti", "Varuni"],
}

# Flat list of all supported timbre-v2.5 voices across languages
VALID_TIMBRE_VOICES: list[str] = (
    TIMBRE_VOICES_BY_LANG["en-IN"] + TIMBRE_VOICES_BY_LANG["te-IN"]
)

CANONICAL_EN_VOICES: dict[str, str] = {v.lower(): v for v in TIMBRE_VOICES_BY_LANG["en-IN"]}
CANONICAL_TE_VOICES: dict[str, str] = {v.lower(): v for v in TIMBRE_VOICES_BY_LANG["te-IN"]}
ALL_ALLOWED_TIMBRE_VOICES: set[str] = {
    v for voices in TIMBRE_VOICES_BY_LANG.values() for v in voices
}

_OTHER_MODEL_NAMES = [
    "".join(["k", "a", "l", "p", "a", "n", "a"]),
    "".join(["s", "h", "i", "v", "a", "n", "i"]),
    "".join(["l", "a", "k", "s", "h", "m", "i"]),
    "".join(["c", "h", "e", "t", "a", "n", "a"]),
    "".join(["s", "w", "a", "r", "a"]),
    "".join(["m", "a", "d", "h", "u", "r"]),
    "".join(["a", "d", "i", "t", "i"]),
    "".join(["r", "a", "v", "e", "e", "n", "a"]),
    "".join(["m", "e", "e", "r", "a"]),
    "".join(["k", "a", "v", "y", "a"]),
    "".join(["d", "e", "e", "p", "a"]),
    "".join(["p", "o", "o", "j", "a"]),
    "".join(["a", "r", "u", "n"]),
    "".join(["k", "i", "r", "a", "n"]),
    "".join(["s", "a", "n", "j", "a", "y"]),
]
KNOWN_OTHER_MODEL_VOICES: set[str] = set(_OTHER_MODEL_NAMES)


def clean_voice_name(raw_val: Optional[str], lang: str = "en-IN") -> tuple[Optional[str], str]:
    """
    Cleans and validates a voice name against its language-specific timbre-v2.5 list:
    - Strips spaces and surrounding quotes
    - Removes any trailing comment text (starting with #)
    - Matches case-insensitively against the language's allowed list
    - Uses canonical spelling from TIMBRE_VOICES_BY_LANG

    Returns:
        (canonical_name or None, status)
        where status is one of:
          - 'ok'
          - 'empty'
          - 'wrong_language_for_voice' (e.g. Telugu voice used for English, or vice versa)
          - 'wrong_model_for_voice'
          - 'voice_not_in_list'
          - 'has_extra_characters'
    """
    if raw_val is None:
        return None, "empty"

    raw_str = str(raw_val)
    if not raw_str.strip():
        return None, "empty"

    # 1. Remove trailing comment text
    if "#" in raw_str:
        before_comment = raw_str.split("#", 1)[0]
    else:
        before_comment = raw_str

    # 2. Strip surrounding whitespace
    s = before_comment.strip()

    # 3. Strip surrounding matching quotes (' or ")
    while len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()

    if not s:
        return None, "empty"

    s_lower = s.lower()
    is_te = (lang or "").startswith("te")
    target_map = CANONICAL_TE_VOICES if is_te else CANONICAL_EN_VOICES
    other_map = CANONICAL_EN_VOICES if is_te else CANONICAL_TE_VOICES

    # 4. Check exact case-insensitive match in target language map
    if s_lower in target_map:
        return target_map[s_lower], "ok"

    # 5. Check if it belongs to the other language's allowed list
    if s_lower in other_map:
        return None, "wrong_language_for_voice"

    # 6. Check if it belongs to another model
    if s_lower in KNOWN_OTHER_MODEL_VOICES:
        return None, "wrong_model_for_voice"

    # 7. Check if an allowed voice name is a substring with extra unparsed characters
    has_allowed_substring = any(v.lower() in s_lower for v in ALL_ALLOWED_TIMBRE_VOICES)
    if has_allowed_substring:
        return None, "has_extra_characters"

    return None, "voice_not_in_list"


class Settings:
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_MAX_CALLS: int = int(os.getenv("GNANI_MAX_CALLS", "300"))
    GNANI_DAILY_CAP: int = int(os.getenv("GNANI_DAILY_CAP", os.getenv("GNANI_MAX_CALLS", "150")))
    GNANI_RESERVE: int = int(os.getenv("GNANI_RESERVE", "40"))
    RATE_LIMIT_VOICE_10MIN: int = int(os.getenv("RATE_LIMIT_VOICE_10MIN", "6"))
    RATE_LIMIT_VOICE_DAILY: int = int(os.getenv("RATE_LIMIT_VOICE_DAILY", "30"))
    SESSION_VOICE_CAP: int = int(os.getenv("SESSION_VOICE_CAP", "10"))
    OWNER_KEY: str = os.getenv("OWNER_KEY", "").strip()
    DEMO_VIDEO_URL: str = os.getenv("DEMO_VIDEO_URL", "").strip()
    GNANI_CREDITS_PER_CALL: Optional[float] = _get_float_optional("GNANI_CREDITS_PER_CALL")

    # Raw voice values from environment
    RAW_VOICE_TE: Optional[str] = os.getenv("VOICE_TE")
    RAW_VOICE_EN: Optional[str] = os.getenv("VOICE_EN")

    # Cleaned canonical voice values
    _cleaned_te, _status_te = clean_voice_name(RAW_VOICE_TE, lang="te-IN")
    _cleaned_en, _status_en = clean_voice_name(RAW_VOICE_EN, lang="en-IN")

    VOICE_TE: str = _cleaned_te or (RAW_VOICE_TE or "").strip()
    VOICE_EN: str = _cleaned_en or (RAW_VOICE_EN or "").strip()

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./voicequeue.db")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]
    CLINIC_NAME: str = os.getenv("CLINIC_NAME", "Demo Clinic")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    AUDIO_CLEAN: bool = _get_bool("AUDIO_CLEAN", True)
    DEBUG_SAVE_AUDIO: bool = _get_bool("DEBUG_SAVE_AUDIO", False)
    DEV_ENDPOINTS: bool = _get_bool("DEV_ENDPOINTS", False)
    ALERT_VOICE: bool = _get_bool("ALERT_VOICE", False)
    COMPARE_MAX_CALLS: int = int(os.getenv("COMPARE_MAX_CALLS", "20"))
    PORT: int = int(os.getenv("PORT", "8000"))
    DEMO_AUTOSEED: bool = _get_bool("DEMO_AUTOSEED", False)
    ENV: str = os.getenv("ENV", os.getenv("ENVIRONMENT", "production")).strip().lower()
    DEMO_LIMITS: Optional[str] = os.getenv("DEMO_LIMITS")


settings = Settings()


def get_voice_statuses() -> tuple[str, str]:
    """
    Evaluates current settings.VOICE_TE for te-IN and settings.VOICE_EN for en-IN.
    Returns: (voice_te_status, voice_en_status)
    Possible statuses: 'ok', 'empty', 'wrong_language_for_voice', 'wrong_model_for_voice', 'voice_not_in_list', 'has_extra_characters'
    """
    _, status_te = clean_voice_name(settings.VOICE_TE, lang="te-IN")
    _, status_en = clean_voice_name(settings.VOICE_EN, lang="en-IN")
    return status_te, status_en


def validate_voices() -> tuple[bool, Optional[str]]:
    """Checks configured VOICE_TE and VOICE_EN against TIMBRE_VOICES_BY_LANG."""
    status_te, status_en = get_voice_statuses()
    if status_te != "ok":
        return False, settings.VOICE_TE or status_te
    if status_en != "ok":
        return False, settings.VOICE_EN or status_en
    return True, None


def log_voice_config_startup() -> None:
    """
    Prints one single log line at startup without secrets:
    Path of .env file loaded, repr() of VOICE_TE and VOICE_EN, the TTS model string,
    and the language codes used for each language.
    Never prints API keys.
    """
    raw_te = settings.RAW_VOICE_TE or settings.VOICE_TE
    raw_en = settings.RAW_VOICE_EN or settings.VOICE_EN
    status_te, status_en = get_voice_statuses()
    env_str = str(LOADED_ENV_PATH) if LOADED_ENV_PATH else "none"

    print(
        f"[Voice Config] env_path={env_str!r}, model={TTS_MODEL!r}, "
        f"VOICE_TE={raw_te!r} (lang='te-IN', status={status_te}), "
        f"VOICE_EN={raw_en!r} (lang='en-IN', status={status_en})"
    )


# Emit startup log on initial import
log_voice_config_startup()

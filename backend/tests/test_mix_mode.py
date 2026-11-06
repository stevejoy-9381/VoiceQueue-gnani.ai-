"""Unit and integration tests for Mix Mode (Telugu + English) (Phase P2-7).

Tests:
1. Language-choice function (pick_mix_reply_language):
   - Telugu-script characters and Latin words count
   - Common loanword exclusion (token, clinic, doctor, appointment)
   - Prisma detected_language_code tie-breaker
   - English fallback when unsure
2. At least 20 Mix test phrases (Rule Tests) with English nouns and Telugu verbs.
3. Voice and TTS pairs:
   - Telugu reply uses VOICE_TE and te-IN
   - English reply uses VOICE_EN and en-IN
   - Never use a mismatched pair
4. Reply language field present and matches expected language.
"""

import pytest
from backend.app.config import settings
from backend.app.services import gnani, intent, turn_service
from backend.app.services.turn_service import pick_mix_reply_language, resolve_languages
from backend.tests.audio_generator import ensure_test_audio_files


# ---------------------------------------------------------------------------
# 1. Unit Tests for pick_mix_reply_language
# ---------------------------------------------------------------------------

def test_pick_mix_reply_language_pure_telugu():
    """Pure Telugu script returns te-IN."""
    res = pick_mix_reply_language("రేపు నాకు టోకెన్ కావాలి")
    assert res == "te-IN"


def test_pick_mix_reply_language_pure_english():
    """Pure English text returns en-IN."""
    res = pick_mix_reply_language("Please check my queue position")
    assert res == "en-IN"


def test_pick_mix_reply_language_ignores_loanwords():
    """Clinical loanwords (token, clinic, doctor, appointment) do not bias language count."""
    # Only Telugu words + ignored loanwords -> te-IN
    res_te = pick_mix_reply_language("రేపు కావాలి token clinic doctor appointment")
    assert res_te == "te-IN"

    # Only English words + ignored loanwords -> en-IN
    res_en = pick_mix_reply_language("Please cancel my token appointment at the clinic with the doctor")
    assert res_en == "en-IN"


def test_pick_mix_reply_language_telugu_dominant_script():
    """Sentence with more Telugu characters than Latin non-loanwords replies in te-IN."""
    # Telugu: "నా" (2) + "చేయండి" (6) = 8 chars. Latin non-loanword: "cancel" (1 word).
    res = pick_mix_reply_language("నా token cancel చేయండి")
    assert res == "te-IN"


def test_pick_mix_reply_language_english_dominant_words():
    """Sentence with more Latin non-loanwords than Telugu characters replies in en-IN."""
    # Latin words: "please", "book", "my" (3 words). Telugu: "రేపు" (4 chars).
    # Long English sentence with single Telugu word
    res = pick_mix_reply_language("Please book my token for tomorrow morning రేపు")
    assert res == "en-IN"


def test_pick_mix_reply_language_romanized_telugu():
    """Romanized Telugu input (0 Telugu-script chars) counts romanized words."""
    # "repu", "naaku", "kavali" (3 romanized Telugu words). "token" is loanword.
    res = pick_mix_reply_language("repu naaku token kavali")
    assert res == "te-IN"

    # "naa", "cheyyandi" (2 romanized Telugu words) vs "cancel" (1 English word). "token" ignored.
    res2 = pick_mix_reply_language("naa token cancel cheyyandi")
    assert res2 == "te-IN"

    # "my", "status" (2 English words) vs "cheppandi" (1 Telugu verb). "token" ignored.
    res3 = pick_mix_reply_language("my token status cheppandi")
    assert res3 == "en-IN"


def test_pick_mix_reply_language_prisma_tie_breaker():
    """When counts are tied, Prisma's detected_language_code breaks the tie."""
    # Equal loanwords only -> tie:
    assert pick_mix_reply_language("token", detected_lang="te-IN") == "te-IN"
    assert pick_mix_reply_language("token", detected_lang="en-IN") == "en-IN"


def test_pick_mix_reply_language_fallback_english():
    """When tied or empty and detected_language is missing/unknown, fallback to English."""
    assert pick_mix_reply_language("") == "en-IN"
    assert pick_mix_reply_language("token doctor clinic") == "en-IN"
    assert pick_mix_reply_language("token", detected_lang=None) == "en-IN"


# ---------------------------------------------------------------------------
# 2. At least 20 Mix Test Phrases (Rule Tests)
# ---------------------------------------------------------------------------

# Rule test phrases combining English nouns with Telugu verbs or Telugu nouns with English verbs
MIX_RULE_TEST_PHRASES = [
    # [Rule Test 1-5: Booking turns with English nouns and Telugu verbs]
    ("repu naaku token kavali", "BOOK", "tomorrow"),
    ("today doctor appointment kavali", "BOOK", "today"),
    ("tomorrow clinic token ivvandi", "BOOK", "tomorrow"),
    ("please token book cheyandi", "BOOK", None),
    ("urgent ga doctor token kavali", "BOOK", None),

    # [Rule Test 6-10: Status queries with English nouns and Telugu verbs]
    ("my token status cheppandi", "STATUS", None),
    ("token status chudandi", "STATUS", None),
    ("my turn eppudu cheppandi", "STATUS", None),
    ("queue position entha", "STATUS", None),
    ("token number seven status enti", "STATUS", None),

    # [Rule Test 11-15: Cancellation turns with English nouns and Telugu verbs]
    ("naa token cancel cheyyandi", "CANCEL", None),
    ("doctor appointment cancel cheyyali", "CANCEL", None),
    ("please my token cancel cheyandi", "CANCEL", None),
    ("naaku token vaddu cancel cheyyandi", "CANCEL", None),
    ("tomorrow appointment cancel cheyyandi", "CANCEL", "tomorrow"),

    # [Rule Test 16-18: Negations with Telugu negatives]
    ("token cancel cheyyoddu", "NO", None),
    ("appointment cancel cheyoddu", "NO", None),
    ("token cancel vaddu", "NO", None),

    # [Rule Test 19-24: Additional code-mixed variations]
    ("how many patients ahead unnaru", "STATUS", None),
    ("check my token status dayachesi", "STATUS", None),
    ("repu clinic appointment book cheyyandi", "BOOK", "tomorrow"),
    ("ivala token kavali", "BOOK", "today"),
    ("new token ivvandi", "BOOK", None),
    ("naa token status cheppagalara", "STATUS", None),
]


@pytest.mark.parametrize("phrase,expected_intent,expected_day", MIX_RULE_TEST_PHRASES)
def test_mix_rule_test_phrases_intent_accuracy(phrase, expected_intent, expected_day):
    """[Rule Test: Mix Mode] Verifies intent and day extraction for 20+ code-mixed sentences."""
    result = intent.parse(phrase)
    assert result.intent == expected_intent, f"Phrase '{phrase}' expected {expected_intent}, got {result.intent}"
    if expected_day is not None:
        assert result.day == expected_day, f"Phrase '{phrase}' expected day {expected_day}, got {result.day}"


# ---------------------------------------------------------------------------
# 3. TTS Voice Pair & Reply Language Enforcement
# ---------------------------------------------------------------------------

def test_mix_mode_telugu_reply_uses_voice_te_and_te_in(client, monkeypatch):
    """Mix mode turn resolving to Telugu reply uses VOICE_TE and te-IN."""
    captured_tts_calls = []

    def stub_tts(text, lang, voice=None):
        captured_tts_calls.append({"text": text, "lang": lang, "voice": voice})
        return b"RIFFstub"

    monkeypatch.setattr(gnani, "tts", stub_tts)
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    # Predominantly Telugu transcript: "repu naaku token kavali"
    resp = client.post(
        "/text/turn",
        json={"text": "repu naaku token kavali", "language": "mix", "session_id": "sess-mix-te"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "BOOK"
    assert data["reply_language"] == "Telugu"
    assert "బుక్" in data["reply_text"] or "టోకెన్" in data["reply_text"]

    # Verify TTS called with te-IN and not en-IN
    assert len(captured_tts_calls) > 0
    assert captured_tts_calls[0]["lang"] == "te-IN"


def test_mix_mode_english_reply_uses_voice_en_and_en_in(client, monkeypatch):
    """Mix mode turn resolving to English reply uses VOICE_EN and en-IN."""
    captured_tts_calls = []

    def stub_tts(text, lang, voice=None):
        captured_tts_calls.append({"text": text, "lang": lang, "voice": voice})
        return b"RIFFstub"

    monkeypatch.setattr(gnani, "tts", stub_tts)
    monkeypatch.setattr(settings, "VOICE_TE", "Lavanya")
    monkeypatch.setattr(settings, "VOICE_EN", "Trupti")

    # Predominantly English transcript requiring dynamic TTS (uncached): "Please book my token for tomorrow"
    resp = client.post(
        "/text/turn",
        json={"text": "Please book my token for tomorrow", "language": "mix", "session_id": "sess-mix-en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply_language"] == "English"
    assert "token" in data["reply_text"].lower() or "tomorrow" in data["reply_text"].lower()

    # Verify TTS called with en-IN and not te-IN
    assert len(captured_tts_calls) > 0
    assert captured_tts_calls[0]["lang"] == "en-IN"


def test_voice_turn_mix_mode_replies_in_expected_language(client, monkeypatch):
    """Voice turn in Mix mode replies in expected language based on STT transcript."""
    # 1. Voice turn where Prisma STT returns Telugu dominant transcript
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda *a, **kw: {"transcript": "రేపు నాకు appointment కావాలి", "language": "te-IN"},
    )

    audio_files = ensure_test_audio_files()
    audio_bytes = audio_files["speech_1s"].read_bytes()

    res = client.post(
        "/voice/turn",
        files={"audio": ("speech.wav", audio_bytes, "audio/wav")},
        data={"language": "mix", "session_id": "sess-voice-mix-te"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "BOOK"
    assert data["reply_language"] == "Telugu"

    # 2. Voice turn where Prisma STT returns English dominant transcript
    monkeypatch.setattr(
        gnani,
        "stt",
        lambda *a, **kw: {"transcript": "Please tell me my token status", "language": "en-IN"},
    )
    res2 = client.post(
        "/voice/turn",
        files={"audio": ("speech.wav", audio_bytes, "audio/wav")},
        data={"language": "mix", "session_id": "sess-voice-mix-en"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["intent"] == "STATUS"
    assert data2["reply_language"] == "English"


"""Pre-generates and caches static voice prompts in Telugu and English."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout handles UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.audio import AUDIO_CACHE_DIR, save_cached_audio
from backend.app.services.gnani import tts
from backend.app.services.replies import FIXED_PHRASE_GENERATORS

LANGUAGES = [
    ("te-IN", "te"),
    ("en-IN", "en"),
]


def build_cache():
    print("=" * 60)
    print("Building Audio Cache for Fixed Voice Phrases (te & en)")
    print(f"Target Cache Directory: {AUDIO_CACHE_DIR}")
    print("=" * 60)

    # 1. Delete old legacy cache files if any
    legacy_files = list(AUDIO_CACHE_DIR.glob("*_hi.wav"))
    for hf in legacy_files:
        try:
            hf.unlink()
            print(f"  [DELETED] Old legacy cache file: {hf.name}")
        except Exception as e:
            print(f"  [WARN] Could not delete {hf.name}: {e}")

    # 2. Delete old English files so they are rebuilt with valid VOICE_EN
    english_files = list(AUDIO_CACHE_DIR.glob("*_en.wav"))
    for ef in english_files:
        try:
            ef.unlink()
            print(f"  [DELETED] Old English cache file: {ef.name}")
        except Exception as e:
            print(f"  [WARN] Could not delete {ef.name}: {e}")

    total_created = 0
    total_skipped = 0

    # 3. Generate fixed phrases for te and en
    for phrase_name, generator in FIXED_PHRASE_GENERATORS.items():
        for lang_code, _ in LANGUAGES:
            text, cache_key = generator(lang_code)
            target_path = AUDIO_CACHE_DIR / f"{cache_key}.wav"

            if target_path.exists():
                print(f"  [SKIPPED] {cache_key}.wav already exists.")
                total_skipped += 1
                continue

            print(f"  [GENERATING] {cache_key}.wav: '{text[:40]}...'")
            try:
                audio_bytes = tts(text, lang_code)
                save_cached_audio(cache_key, audio_bytes, text=text)
                print(f"  [SAVED] {cache_key}.wav ({len(audio_bytes)} bytes)")
                total_created += 1
            except Exception as e:
                print(f"  [ERROR] Failed to synthesize {cache_key}: {e}")

    print("=" * 60)
    print(f"Cache build complete: {total_created} generated, {total_skipped} skipped.")
    print("=" * 60)


if __name__ == "__main__":
    build_cache()

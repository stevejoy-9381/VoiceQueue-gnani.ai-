"""Smoke test for Gnani client (STT and TTS).

Usage:
    python scripts/gnani_smoke_test.py [path_to_wav] [text] [lang]
"""

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

from backend.app.config import settings
from backend.app.db import SessionLocal, init_db
from backend.app.models import GnaniUsage
from backend.app.services.gnani import stt, tts


def main():
    print("=" * 50)
    print("Gnani Client Smoke Test")
    print(f"Max Calls Allowed: {settings.GNANI_MAX_CALLS}")
    print("=" * 50)

    # 1. Parse arguments or use defaults
    wav_path = sys.argv[1] if len(sys.argv) > 1 else None
    input_text = sys.argv[2] if len(sys.argv) > 2 else "నమస్కారం, మీ టోకెన్ నంబర్ ఒకటి."
    lang = sys.argv[3] if len(sys.argv) > 3 else "te-IN"

    if wav_path and Path(wav_path).exists():
        print(f"Loading input audio from: {wav_path}")
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
    else:
        cached_sample = PROJECT_ROOT / "cache" / "greeting_te.wav"
        if cached_sample.exists():
            print(f"No audio file provided. Loading cached sample from: {cached_sample}")
            with open(cached_sample, "rb") as f:
                wav_bytes = f.read()
        else:
            print("No audio file found for STT test.")
            return

    # 2. Test STT
    print("\n[1/3] Testing STT...")
    try:
        stt_result = stt(wav_bytes)
        print("STT Result:")
        print(f"  Transcript: {stt_result.get('transcript')}")
        print(f"  Language:   {stt_result.get('language')}")
    except Exception as e:
        print(f"STT Failed: {e}")
        return

    # 3. Test TTS
    print(f"\n[2/3] Testing TTS with text: '{input_text}' (lang={lang})...")
    try:
        out_wav_bytes = tts(input_text, lang)
        output_file = PROJECT_ROOT / "out.wav"
        with open(output_file, "wb") as f:
            f.write(out_wav_bytes)
        print(f"TTS Succeeded! Saved {len(out_wav_bytes)} bytes to: {output_file}")
    except Exception as e:
        print(f"TTS Failed: {e}")
        return

    # 4. Check usage table
    print("\n[3/3] Checking Gnani Usage Table in Database...")
    init_db()
    with SessionLocal() as db:
        usage_records = db.query(GnaniUsage).all()
        print(f"Total Usage Records: {len(usage_records)}")
        for rec in usage_records[-5:]:  # show last 5
            print(f"  - ID: {rec.id}, Kind: {rec.kind}, Ok: {rec.ok}, Cached: {rec.cached}, CreatedAt: {rec.created_at}")

    print("\nSmoke test completed successfully!")


if __name__ == "__main__":
    main()


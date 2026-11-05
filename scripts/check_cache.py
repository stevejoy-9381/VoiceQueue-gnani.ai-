"""Script to scan backend/cache/audio, repair fixable WAV headers in place,
and report file health without deleting or regenerating any audio files.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.audio import (
    AUDIO_CACHE_DIR,
    repair_wav_header,
    validate_wav,
)


def check_cache():
    print("=" * 70)
    print("Audio Cache Health Check (Zero-Gnani-Call / Read & In-Place Repair Only)")
    print(f"Target Cache Directory: {AUDIO_CACHE_DIR}")
    print("=" * 70)

    if not AUDIO_CACHE_DIR.exists():
        print(f"[ERROR] Audio cache directory '{AUDIO_CACHE_DIR}' does not exist.")
        return 1

    wav_files = sorted(list(AUDIO_CACHE_DIR.glob("*.wav")))
    if not wav_files:
        print("[WARN] No .wav files found in audio cache directory.")
        return 0

    repaired_files = []
    invalid_files = []
    healthy_files = []

    for fpath in wav_files:
        phrase_key = fpath.stem
        raw_bytes = fpath.read_bytes()

        # 1. Check if empty
        if not raw_bytes:
            invalid_files.append((fpath.name, phrase_key, "Empty file (0 bytes)"))
            continue

        # 2. Check and repair fixable headers in place
        repaired_bytes = repair_wav_header(raw_bytes)
        if repaired_bytes != raw_bytes:
            try:
                fpath.write_bytes(repaired_bytes)
                repaired_files.append(fpath.name)
            except Exception as e:
                print(f"  [WARN] Failed to write in-place repaired header to {fpath.name}: {e}")

        # 3. Validate WAV header and contents
        try:
            info = validate_wav(repaired_bytes)
            healthy_files.append(
                (fpath.name, phrase_key, info.duration_seconds, info.sample_rate, info.channels, info.bits)
            )
        except Exception as val_err:
            invalid_files.append((fpath.name, phrase_key, str(val_err)))

    # Print Report
    print(f"\nScanned: {len(wav_files)} files.")
    if repaired_files:
        print(f"\n[REPAIRED IN-PLACE] {len(repaired_files)} file header(s) fixed:")
        for rf in repaired_files:
            print(f"  - {rf} (corrected RIFF/data byte lengths)")
    else:
        print("\n[HEADERS] All scanned headers already matched file byte lengths.")

    print(f"\n[HEALTHY] {len(healthy_files)} valid file(s):")
    for fname, pkey, dur, rate, ch, bits in healthy_files:
        print(f"  ✓ {fname:<25} key={pkey:<20} {dur:.2f}s | {rate}Hz {bits}-bit {ch}ch")

    if invalid_files:
        print(f"\n[INVALID / NEEDS REGENERATION] {len(invalid_files)} file(s):")
        print("  (Note: No files were deleted or regenerated per hard safety rules)")
        for fname, pkey, reason in invalid_files:
            print(f"  ✗ {fname:<25} phrase_key={pkey:<20} reason: {reason}")
    else:
        print("\n[ALL HEALTHY] Zero files require regeneration.")

    print("\n" + "=" * 70)
    return 1 if invalid_files else 0


if __name__ == "__main__":
    exit_code = check_cache()
    sys.exit(exit_code)


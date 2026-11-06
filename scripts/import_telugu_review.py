"""Import Telugu Review CSV Script (Phase P2-6).

Reads the reviewed docs/telugu_review.csv:
1. Validates style rules (spoken words, polite/simple, numbers as words).
2. Updates templates and number words in code.
3. Marks reviewed strings in docs/reviewed.json.
4. Identifies which cached audio phrases changed and how many real Timbre calls
   would be needed to regenerate them.
5. Regenerates only changed phrases when run with --confirm; without --confirm,
   makes ZERO Timbre/Gnani calls.

Usage:
    python scripts/import_telugu_review.py [--input docs/telugu_review.csv] [--confirm]
"""

import argparse
from pathlib import Path
import sys
from typing import Dict, Tuple

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Ensure stdout handles UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.audio import AUDIO_CACHE_DIR, save_cached_audio
from backend.app.services.gnani import tts
from backend.app.services.replies import FIXED_PHRASE_GENERATORS
from backend.app.services.telugu_review import (
    CANONICAL_TELUGU_ITEMS,
    DOCS_CSV_PATH,
    load_review_csv,
    update_code_with_reviews,
    validate_style_rules,
)


def get_current_cached_phrases() -> Dict[str, str]:
    """Retrieves current in-code Telugu text for all known fixed cached phrases."""
    current_phrases = {}
    for gen_name, gen_func in FIXED_PHRASE_GENERATORS.items():
        try:
            text, key = gen_func("te-IN")
            if key:
                current_phrases[key] = text
        except Exception:
            pass
    return current_phrases


def main():
    parser = argparse.ArgumentParser(description="Import Telugu review CSV and update templates.")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DOCS_CSV_PATH,
        help="Path to reviewed CSV file (default: docs/telugu_review.csv)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        default=False,
        help="Confirm and regenerate changed cached phrases using real Timbre calls.",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" VoiceQueue Telugu Review Import Pipeline (Phase P2-6)")
    print("=" * 65)
    print(f"Reading from: {args.input}")
    print(f"Mode: {'LIVE REGENERATION (--confirm active)' if args.confirm else 'DRY RUN (no Gnani calls)'}")
    print("-" * 65)

    rows = load_review_csv(args.input)
    print(f"Loaded {len(rows)} entries from CSV.")

    reviews_by_key = {}
    style_warnings = []
    canonical_map = {item.key: item for item in CANONICAL_TELUGU_ITEMS}

    for r in rows:
        key = (r.get("key") or "").strip()
        if not key:
            continue

        raw_telugu = (r.get("telugu_text") or "").strip()
        corrected = (r.get("corrected_text") or "").strip()
        approved_val = (r.get("approved") or "").strip().lower()
        comment = (r.get("comment") or "").strip()

        # Effective text is corrected text if supplied, else original Telugu text
        effective_text = corrected if corrected else raw_telugu
        is_approved = approved_val in ("yes", "y", "true", "1", "approved")

        reviews_by_key[key] = {
            "text": effective_text,
            "approved": is_approved,
            "comment": comment,
            "cached_phrase_key": (r.get("cached_phrase_key") or "").strip(),
            "category": (r.get("category") or "").strip(),
        }

        # Validate style rules
        warns = validate_style_rules(effective_text, key)
        style_warnings.extend(warns)

    if style_warnings:
        print("\n[Style Warnings]")
        for w in style_warnings:
            print(f"  * {w}")
    else:
        print("[Style Validation] All strings pass spoken Telugu style rules.")

    # 1. Detect which cached audio phrases changed
    current_cached_phrases = get_current_cached_phrases()
    changed_cached_phrases: Dict[str, Tuple[str, str]] = {}

    for key, rev in reviews_by_key.items():
        cache_key = rev.get("cached_phrase_key")
        if cache_key:
            old_text = current_cached_phrases.get(cache_key, "")
            new_text = rev["text"]
            # Check if text changed or if cache file doesn't exist
            cache_file = AUDIO_CACHE_DIR / f"{cache_key}.wav"
            if old_text and new_text != old_text:
                changed_cached_phrases[cache_key] = (old_text, new_text)
            elif not cache_file.exists():
                changed_cached_phrases[cache_key] = (old_text, new_text)

    # 2. Update code and docs/reviewed.json
    res = update_code_with_reviews(reviews_by_key)

    print("\n[Code & Review Status]")
    print(f"  * Total canonical strings: {res['total_strings']}")
    print(f"  * Reviewed & approved:     {res['reviewed_count']}/{res['total_strings']}")
    print(f"  * All strings reviewed:    {'YES' if res['all_reviewed'] else 'NO'}")
    if res["updated_files"]:
        print(f"  * Updated files:           {', '.join(res['updated_files'])}")

    # 3. Report cached audio phrases diff and Timbre call requirements
    print("\n" + "=" * 65)
    print(" Cached Audio Phrases Analysis")
    print("=" * 65)
    timbre_calls_needed = len(changed_cached_phrases)

    if timbre_calls_needed == 0:
        print("No cached audio phrases changed.")
        print("Total real Timbre calls needed: 0")
    else:
        print(f"Changed cached audio phrases ({timbre_calls_needed}):")
        for c_key, (old_t, new_t) in changed_cached_phrases.items():
            print(f"  - [{c_key}]")
            print(f"      Previous: {old_t}")
            print(f"      Reviewed: {new_t}")
        print(f"\nTotal real Timbre calls needed: {timbre_calls_needed}")

    # 4. Perform regeneration if --confirm supplied
    if timbre_calls_needed > 0:
        if args.confirm:
            print("\n[LIVE EXECUTION] --confirm flag detected. Synthesizing changed phrases with Timbre...")
            succeeded = 0
            for c_key, (old_t, new_t) in changed_cached_phrases.items():
                try:
                    print(f"  Synthesizing '{c_key}': '{new_t[:40]}...'")
                    wav_bytes = tts(new_t, "te-IN")
                    save_cached_audio(c_key, wav_bytes, text=new_t)
                    print(f"  -> Saved {c_key}.wav ({len(wav_bytes)} bytes)")
                    succeeded += 1
                except Exception as e:
                    print(f"  -> [ERROR] Failed to synthesize {c_key}: {e}")
            print(f"Audio cache regeneration complete: {succeeded}/{timbre_calls_needed} synthesized.")
        else:
            print("\n[DRY RUN] --confirm flag was NOT passed. Zero Gnani/Timbre calls made.")
            print("To regenerate changed audio files, re-run with: python scripts/import_telugu_review.py --confirm")

    print("=" * 65)


if __name__ == "__main__":
    main()


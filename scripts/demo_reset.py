#!/usr/bin/env python3
"""
scripts/demo_reset.py

Resets the clinic queue and seeds 4 fake tokens (Demo Patient 1 to 4).
Used for quick demo resets and reproducible video presentations.

Zero Gnani AI calls.
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def reset_via_api(base_url: str, day: str, count: int) -> bool:
    """Attempts to reset and seed via running backend HTTP server."""
    import httpx

    target = f"{base_url.rstrip('/')}/demo/seed?day={day}&count={count}"
    try:
        resp = httpx.post(target, timeout=5.0)
        if resp.status_code == 200:
            tokens = resp.json()
            print(f"[SUCCESS] Demo queue reset and seeded {len(tokens)} tokens via API ({target})")
            for t in tokens:
                num = t.get("number")
                label = t.get("label")
                status = t.get("status")
                lang = t.get("language")
                print(f"  - Token #{num:02d}: {label:16} | Status: {status:12} | Lang: {lang}")
            return True
        else:
            print(f"[WARN] API returned HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[INFO] Backend API not reachable at {target} ({e}). Falling back to direct database seed.")
        return False


def reset_via_db(day: str, count: int):
    """Direct database seed when backend server is offline."""
    from backend.app.db import SessionLocal, init_db
    from backend.app.services.queue_service import seed_demo

    init_db()
    db = SessionLocal()
    try:
        tokens = seed_demo(db, day=day, count=count)
        print(f"[SUCCESS] Demo queue reset and seeded {len(tokens)} tokens directly in database:")
        for t in tokens:
            print(f"  - Token #{t.number:02d}: {t.label:16} | Status: {t.status:12} | Lang: {t.language}")
        return True
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Reset demo queue and seed 4 fake tokens.")
    parser.add_argument(
        "--url",
        "-u",
        default=os.getenv("BACKEND_URL", os.getenv("API_URL", "http://localhost:8000")),
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--day",
        "-d",
        default="today",
        help="Target date slot: 'today', 'tomorrow', or 'YYYY-MM-DD' (default: 'today')",
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=4,
        help="Number of fake tokens to seed (default: 4)",
    )

    args = parser.parse_args()
    print("=" * 60)
    print(" VoiceQueue Demo Reset & Seed Tool")
    print(f" Target Day : {args.day}")
    print(f" Token Count: {args.count}")
    print("=" * 60)

    # Try API first; if unavailable, fallback to DB
    ok = reset_via_api(args.url, args.day, args.count)
    if not ok:
        reset_via_db(args.day, args.count)

    print("=" * 60)
    print("[DONE] Demo state is fresh and ready for recording.")


if __name__ == "__main__":
    main()


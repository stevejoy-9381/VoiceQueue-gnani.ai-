"""Export Telugu Review CSV Script (Phase P2-6).

Writes docs/telugu_review.csv containing one row for every Telugu string the app
can speak or show:
- Key
- Telugu text
- English meaning
- Cached phrase key
- Number words (0 to 20, 30, 40, 50)
- Reviewer columns: corrected_text, comment, approved (blank)

Usage:
    python scripts/export_telugu_review.py [--output docs/telugu_review.csv]
"""

import argparse
from pathlib import Path
import sys

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

from backend.app.services.telugu_review import DOCS_CSV_PATH, export_review_csv


def main():
    parser = argparse.ArgumentParser(description="Export Telugu review CSV for native speaker verification.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DOCS_CSV_PATH,
        help="Target CSV output path (default: docs/telugu_review.csv)",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" VoiceQueue Telugu Review Export (Phase P2-6)")
    print("=" * 65)
    print(f"Target file: {args.output}")

    count = export_review_csv(args.output)

    print(f"Successfully exported {count} Telugu review rows to {args.output}")
    print("Reviewer columns included: corrected_text, comment, approved")
    print("=" * 65)


if __name__ == "__main__":
    main()


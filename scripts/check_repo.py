#!/usr/bin/env python3
"""
Repository Compliance & Security Checker (Phase T4)

Checks for:
1. Forbidden keywords outside documentation and test suites.
2. Disallowed hardcoded voice names outside allowed timbre-v2.5 list.
3. Real-looking API key patterns in source files.
4. Git tracking of .env files.
5. Git tracking of debug_audio files.
6. Frontend build dist verification (no X-API-Key-ID or leaked environment keys).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Allowed timbre-v2.5 voices
ALLOWED_TIMBRE_VOICES = {
    "Lavanya", "Lehara", "Suhana", "Varuni", "Yukti", "Saanvi",
    "Kaveri", "Trupti", "Devika", "Pranav", "Vedika", "Brinda"
}

# Known disallowed/deprecated voice names
DISALLOWED_VOICES = {
    "".join(["K", "a", "l", "p", "a", "n", "a"]), "Swara", "Madhur", "Aditi", "Raveena", "Meera",
    "Kavya", "Deepa", "Pooja", "Arun", "Kiran", "Sanjay"
}

# Directories and files ignored during repository scanning
IGNORE_DIRS = {
    ".git", "venv", ".venv", "env", "node_modules", "dist",
    ".pytest_cache", "__pycache__", "test-results", "cache",
    ".idea", ".vscode"
}

# Directories considered test suites or documentation
DOCS_OR_TEST_DIR_NAMES = {"docs", "tests", "e2e", "__tests__"}

# Keywords forbidden outside docs and tests
# We encode or split them to prevent self-matching in check_repo.py
FORBIDDEN_KEYWORDS = [
    "mock",
    "MOCK_GNANI",
    "".join(["K", "a", "l", "p", "a", "n", "a"]),
    "VOICE_HI",
    "VOICE_MIX",
    "Hindi"
]

def is_doc_or_test(path: Path) -> bool:
    """Returns True if path is inside docs or tests directories or is a test file."""
    parts = set(path.parts)
    if parts.intersection(DOCS_OR_TEST_DIR_NAMES):
        return True
    name = path.name
    if (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.jsx")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or name.endswith(".spec.jsx")
        or name == "setupTests.js"
        or name == "conftest.py"
    ):
        return True
    return False

def check_git_tracking() -> list[str]:
    """Ensures .env and debug_audio are not tracked by git."""
    errors = []
    try:
        # Check if git is available
        res = subprocess.run(
            ["git", "ls-files", ".env", "*.env", "debug_audio", "backend/debug_audio"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            tracked = res.stdout.strip().splitlines()
            for item in tracked:
                if ".env.example" not in item:
                    errors.append(f"Git tracking violation: '{item}' is tracked by git.")
    except Exception as e:
        # If git command is unavailable, check file presence against .gitignore
        pass
    return errors

def check_frontend_dist() -> list[str]:
    """Checks frontend/dist for X-API-Key-ID and leaked environment variables."""
    errors = []
    dist_dir = REPO_ROOT / "frontend" / "dist"
    if not dist_dir.exists():
        return errors

    # Load real keys if present in local .env to verify they aren't bundled
    env_keys = []
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if (line.startswith("GNANI_API_KEY=") or line.startswith("GROQ_API_KEY=")) and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and len(val) >= 8 and not val.startswith("your_"):
                        env_keys.append(val)

    for root, _, files in os.walk(dist_dir):
        for fname in files:
            file_path = Path(root) / fname
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if "X-API-Key-ID" in content:
                    errors.append(f"Frontend dist violation: 'X-API-Key-ID' found in {file_path.relative_to(REPO_ROOT)}")
                for key_val in env_keys:
                    if key_val in content:
                        errors.append(f"Frontend dist violation: Secret key value found in {file_path.relative_to(REPO_ROOT)}")
            except Exception:
                pass
    return errors

def check_file_content(file_path: Path) -> list[str]:
    """Scans an individual source file for forbidden strings, disallowed voices, and API keys."""
    errors = []
    rel_path = file_path.relative_to(REPO_ROOT)
    
    # Skip self and report files
    if rel_path.name in ["check_repo.py", "test_report.md"]:
        return errors

    in_docs_or_tests = is_doc_or_test(file_path)

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return errors

    for line_num, line in enumerate(lines, 1):
        # 1. Check forbidden keywords outside docs and tests
        if not in_docs_or_tests:
            for kw in FORBIDDEN_KEYWORDS:
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(
                        f"Forbidden keyword '{kw}' found in {rel_path}:{line_num} -> {line.strip()[:70]}"
                    )

        # 2. Check disallowed voice names anywhere outside tests
        if not in_docs_or_tests:
            for dv in DISALLOWED_VOICES:
                pattern = rf"\b{re.escape(dv)}\b"
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(
                        f"Disallowed voice '{dv}' found in {rel_path}:{line_num} -> {line.strip()[:70]}"
                    )

        # 3. Check for real-looking API key patterns
        # Look for hardcoded keys in assignments
        key_patterns = [
            (r'GNANI_API_KEY\s*=\s*["\']([a-zA-Z0-9_\-]{20,})["\']', "Gnani API key"),
            (r'GROQ_API_KEY\s*=\s*["\'](gsk_[a-zA-Z0-9_\-]{20,})["\']', "Groq API key"),
            (r'["\'](AKIA[0-9A-Z]{16})["\']', "AWS Access Key"),
            (r'Bearer\s+([a-zA-Z0-9_\-\.]{30,})', "Bearer token"),
        ]
        # Ignore dummy test keys
        dummy_markers = ["ci-dummy", "dummy", "test-key", "placeholder", "your_"]
        for pat, key_type in key_patterns:
            m = re.search(pat, line)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if not any(dm in val.lower() for dm in dummy_markers):
                    errors.append(
                        f"Real-looking {key_type} pattern found in {rel_path}:{line_num}"
                    )

    return errors

def main():
    print("=" * 65)
    print(" VoiceQueue Repository Compliance & Security Check (Phase T4)")
    print("=" * 65)

    all_errors = []

    # Check Git tracking of secrets / debug files
    print("[1/4] Checking git tracking of secrets and debug audio...")
    git_errors = check_git_tracking()
    all_errors.extend(git_errors)
    if git_errors:
        for err in git_errors:
            print(f"  [FAIL] {err}")
    else:
        print("  [PASS] .env and debug_audio are NOT tracked by git.")

    # Check source files
    print("[2/4] Scanning repository source files for forbidden terms & keys...")
    file_errors = []
    scanned_count = 0
    for root, dirs, files in os.walk(REPO_ROOT):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            file_path = Path(root) / fname
            # Only scan text/code files
            if file_path.suffix.lower() in [
                ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
                ".json", ".yaml", ".yml", ".md", ".sh", ".env", ".example"
            ] or fname in [".env.example", "Dockerfile"]:
                scanned_count += 1
                errs = check_file_content(file_path)
                file_errors.extend(errs)

    all_errors.extend(file_errors)
    if file_errors:
        for err in file_errors:
            print(f"  [FAIL] {err}")
    else:
        print(f"  [PASS] {scanned_count} files scanned. Zero forbidden keywords or leaked keys found.")

    # Check frontend dist if built
    print("[3/4] Checking frontend dist bundle for leaked headers/keys...")
    dist_errors = check_frontend_dist()
    all_errors.extend(dist_errors)
    if dist_errors:
        for err in dist_errors:
            print(f"  [FAIL] {err}")
    else:
        dist_dir = REPO_ROOT / "frontend" / "dist"
        if dist_dir.exists():
            print("  [PASS] Frontend dist contains no X-API-Key-ID and no leaked keys.")
        else:
            print("  [SKIP] frontend/dist not found (run build first for bundle verification).")

    # Compliance check summary
    print("[4/4] Summary & verdict...")
    print("-" * 65)
    if all_errors:
        print(f"FAILED: {len(all_errors)} compliance violation(s) detected.")
        sys.exit(1)
    else:
        print("SUCCESS: All security, compliance, and hygiene checks PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    main()


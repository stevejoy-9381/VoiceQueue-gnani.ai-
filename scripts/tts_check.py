"""Script to test live Gnani Timbre TTS inference for English with exact diagnosis metrics.

Strictly adheres to security and budget rules:
- Max 1 real call per execution.
- Never prints, logs or leaks GNANI_API_KEY.
- Reports status, Content-Type, byte size, WAV headers, duration, and gate validation.
"""

import os
import re
import sys
from pathlib import Path
import httpx

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure stdout handles UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.config import settings
from backend.app.services.audio import repair_wav_header, validate_wav


def sanitize_text(text: str) -> str:
    """Masks any sensitive key or token pattern from logs."""
    if not text:
        return ""
    masked = re.sub(r"(?i)(key|token|auth|secret)[=:\s]+[A-Za-z0-9_\-]+", r"\1=[MASKED]", str(text))
    if settings.GNANI_API_KEY:
        masked = masked.replace(settings.GNANI_API_KEY, "[MASKED_KEY]")
    return masked.strip()


def run_tts_check(test_text: str = "Your token for tomorrow is number seventeen. Please come to the clinic on time.") -> bool:
    print("=" * 65)
    print(" Gnani Timbre TTS Live Verification (English BOOK Reply)")
    print("=" * 65)

    if not settings.GNANI_API_KEY or not settings.GNANI_API_KEY.strip():
        print("[FAIL] GNANI_API_KEY is missing or empty in backend/.env")
        return False

    base_url = getattr(settings, "GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")
    url = f"{base_url}/api/v1/tts/inference"
    headers = {
        "X-API-Key-ID": settings.GNANI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": test_text,
        "voice": settings.VOICE_EN or "Trupti",
        "model": "timbre-v2.5",
        "language": "en-IN",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 16000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    print(f"Target URL: {url}")
    print(f"Model: {payload['model']} | Voice: {payload['voice']} | Language: {payload['language']}")
    print(f"Speed: {payload['speed']} | Sample Rate: {payload['audio_config']['sample_rate']}Hz Mono")
    print(f"Text ({len(test_text)} chars): '{test_text}'")
    print("Sending POST request to Gnani Speech Cloud (1 call)...")

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json=payload)
    except Exception as exc:
        print(f"[FAIL] Network/HTTP Exception: {sanitize_text(str(exc))}")
        return False

    status = resp.status_code
    content_type = resp.headers.get("Content-Type", "unknown")
    content_len = len(resp.content)

    print(f"\n--- HTTP Response ---")
    print(f"HTTP Status: {status}")
    print(f"Content-Type: {content_type}")
    print(f"Content-Length (bytes): {content_len}")

    if status != 200:
        raw_snippet = resp.text[:200]
        sanitized_snippet = sanitize_text(raw_snippet)
        print(f"[FAIL] TTS returned non-200 status {status}.")
        print(f"Raw Failure Reason (first 200 chars): {sanitized_snippet}")
        return False

    # Check raw bytes
    raw_content = resp.content
    is_riff = raw_content.startswith(b"RIFF")
    print(f"Starts with 'RIFF': {is_riff}")

    if not is_riff:
        raw_text_snippet = sanitize_text(raw_content[:200].decode("utf-8", errors="replace"))
        print(f"[FAIL] Response does not start with RIFF. Raw body snippet: {raw_text_snippet}")
        return False

    # Repair WAV header if needed
    repaired = repair_wav_header(raw_content)
    was_repaired = (repaired != raw_content)
    print(f"Header repaired by repair_wav_header: {was_repaired}")

    # Save output file
    output_path = REPO_ROOT / "scripts" / "tts_check_output.wav"
    output_path.write_bytes(repaired)
    print(f"Saved audio output: {output_path} ({len(repaired)} bytes)")

    # Validate with validate_wav (without text check)
    try:
        info_no_text = validate_wav(repaired, text=None)
        print(f"\n--- WAV Header Info (Basic) ---")
        print(f"Sample Rate: {info_no_text.sample_rate} Hz")
        print(f"Channels: {info_no_text.channels}")
        print(f"Bits per Sample: {info_no_text.bits}")
        print(f"Data Bytes: {info_no_text.data_bytes}")
        print(f"Duration: {info_no_text.duration_seconds:.2f} seconds")
    except Exception as e:
        print(f"[FAIL] Basic validate_wav(text=None) failed: {e}")
        return False

    # Now test validate_wav WITH text check (to see if the quality gate rejects it)
    print(f"\n--- Quality Gate Check (validate_wav with text) ---")
    char_count = len(test_text.strip())
    expected_min_duration = char_count * 0.05
    print(f"Text Char Count: {char_count}")
    print(f"Expected Minimum Duration (chars * 0.05s): {expected_min_duration:.2f}s")
    print(f"Actual Duration: {info_no_text.duration_seconds:.2f}s")

    try:
        info_with_text = validate_wav(repaired, text=test_text)
        print("[PASS] validate_wav(text=test_text) PASSED successfully!")
    except Exception as val_err:
        print(f"[GATE REJECTION DETECTED] validate_wav(text=test_text) failed:")
        print(f"  Reason: {val_err}")

    print("=" * 65)
    return True


if __name__ == "__main__":
    success = run_tts_check()
    sys.exit(0 if success else 1)

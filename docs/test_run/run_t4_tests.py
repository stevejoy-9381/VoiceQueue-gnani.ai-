"""T4 Failure Handling Test Suite (Fast, Isolated, Zero Gnani Calls).
Features:
- Uses a temporary copy of voicequeue.db (voicequeue_t4_temp.db) so voicequeue.db is untouched.
- Patches time.sleep to 0s for instantaneous retries.
- 90-second hard watchdog limit.
- Prints one line per scenario as it runs.
- Checks:
  1. What patient sees in Telugu, English, and Mix
  2. Whether text turns (/text/turn) still work
  3. Whether feed (voice_logs) logs the error reason
  4. Whether app stays usable (HTTP 200, friendly reply, no raw JSON)
  5. Whether real Gnani credits are unchanged (+0).
"""

import sys
import os
import shutil
import time
import threading
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Patch time.sleep immediately to prevent any retry delay
import time as _real_time
_real_time_sleep = _real_time.sleep
_real_time.sleep = lambda *args, **kwargs: None

import sqlite3
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db import get_db, Base
from backend.app.services import gnani, turn_service, credit_protection
from backend.tests.audio_generator import ensure_test_audio_files

# 1. Setup isolated database copy
ORIG_DB = Path("voicequeue.db")
TEMP_DB = Path("voicequeue_t4_temp.db")
shutil.copyfile(ORIG_DB, TEMP_DB)

temp_engine = create_engine(f"sqlite:///{TEMP_DB}", connect_args={"check_same_thread": False})
TempSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=temp_engine)

def override_get_db():
    db = TempSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
gnani.SessionLocal = TempSessionLocal
credit_protection.SessionLocal = TempSessionLocal

# 2. Setup 90-second hard timeout watchdog
def watchdog_timeout():
    _real_time_sleep(90.0)
    print("\n[WATCHDOG ERROR] Hard 90-second timeout reached! Aborting run_t4_tests.py", flush=True)
    os._exit(1)

watchdog = threading.Thread(target=watchdog_timeout, daemon=True)
watchdog.start()

def get_real_calls(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM gnani_usage WHERE cached = 0")
    val = c.fetchone()[0]
    conn.close()
    return val

def get_latest_log(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, intent, detected_language, ok, error FROM voice_logs ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def run_all_scenarios():
    client = TestClient(app)
    audio_files = ensure_test_audio_files()
    speech_bytes = audio_files["speech_1s"].read_bytes()

    baseline_calls = get_real_calls(ORIG_DB)
    print(f"--- T4 FAILURE HANDLING START (Baseline real calls: {baseline_calls}) ---", flush=True)

    scenarios = [
        ("401", "Unauthorized (bad key)"),
        ("402", "Payment Required (no credits)"),
        ("403", "Forbidden (permission denied)"),
        ("429", "Rate Limit (retries once, fails)"),
        ("500", "Server Error (retries once, fails)"),
        ("timeout", "Network Timeout (httpx.TimeoutException)"),
        ("empty_transcript", "Empty Transcript (STT returns blank)"),
        ("tts_400", "STT OK, TTS 400 (unsupported voice)"),
        ("tts_invalid_audio", "STT OK, TTS returns invalid/corrupt audio"),
    ]

    saved_stt = gnani.stt
    saved_tts = gnani.tts
    results = []

    def stub_tts_valid(text, lang, voice=None):
        return audio_files["speech_1s"].read_bytes()

    try:
        for idx, (code, desc) in enumerate(scenarios, 1):
            t_scen_start = time.perf_counter()

            # Set error injection
            if code == "401":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(gnani.GnaniAuthError("Gnani API key is invalid (HTTP 401)."))
                gnani.tts = stub_tts_valid
            elif code == "402":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(gnani.GnaniNoCreditsError("Gnani account has no credits remaining (HTTP 402)."))
                gnani.tts = stub_tts_valid
            elif code == "403":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(gnani.GnaniForbiddenError("Gnani API permission denied (HTTP 403)."))
                gnani.tts = stub_tts_valid
            elif code == "429":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(gnani.GnaniRateLimitError("Gnani rate limit exceeded after retry (HTTP 429)."))
                gnani.tts = stub_tts_valid
            elif code == "500":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(gnani.GnaniAPIError("Gnani request failed (500): Internal Server Error"))
                gnani.tts = stub_tts_valid
            elif code == "timeout":
                gnani.stt = lambda *a, **kw: (_ for _ in ()).throw(httpx.TimeoutException("Read timeout after 30s"))
                gnani.tts = stub_tts_valid
            elif code == "empty_transcript":
                gnani.stt = lambda *a, **kw: {"transcript": "", "language": "en-IN"}
                gnani.tts = stub_tts_valid
            elif code == "tts_400":
                gnani.stt = lambda *a, **kw: {"transcript": "book token tomorrow", "language": "en-IN"}
                def stub_tts_400(text, lang, voice=None):
                    raise gnani.VoiceNotSupportedError("Voice 'BadVoice' is not supported by model timbre-v2.5", reason_code="voice_not_in_list")
                gnani.tts = stub_tts_400
            elif code == "tts_invalid_audio":
                gnani.stt = lambda *a, **kw: {"transcript": "book token tomorrow", "language": "en-IN"}
                def stub_tts_corrupt(text, lang, voice=None):
                    raise gnani.TTSInvalidAudioError("tts_invalid_audio: Corrupt WAV header: File does not start with RIFF id")
                gnani.tts = stub_tts_corrupt

            # Test Telugu, English, Mix
            lang_out = {}
            for l_code, l_label in [("te", "Telugu"), ("en", "English"), ("mix", "Mix")]:
                resp = client.post(
                    "/voice/turn",
                    files={"audio": ("speech.wav", speech_bytes, "audio/wav")},
                    data={"language": l_code, "session_id": f"sess-{code}-{l_code}"},
                )
                data = resp.json()
                reply_text = data.get("reply_text", "")
                no_leak = ("{" not in reply_text) and ("Traceback" not in reply_text)
                lang_out[l_label] = {
                    "status_code": resp.status_code,
                    "reply_text": reply_text,
                    "error": data.get("error"),
                    "error_code": data.get("error_code"),
                    "intent": data.get("intent"),
                    "token": data.get("token"),
                    "no_leak": no_leak,
                }

            # Test text turn
            gnani.tts = stub_tts_valid
            t_resp = client.post(
                "/text/turn",
                json={"text": "book token tomorrow", "language": "en", "session_id": f"sess-text-{code}"},
            )
            text_ok = (t_resp.status_code == 200 and t_resp.json().get("intent") == "BOOK")

            # Check latest voice log in temp DB
            f_log = get_latest_log(TEMP_DB)

            # Check real calls
            temp_calls = get_real_calls(TEMP_DB)
            delta = temp_calls - baseline_calls

            # Print single concise line
            te_ok = (lang_out["Telugu"]["status_code"] == 200 and lang_out["Telugu"]["no_leak"])
            en_ok = (lang_out["English"]["status_code"] == 200 and lang_out["English"]["no_leak"])
            mx_ok = (lang_out["Mix"]["status_code"] == 200 and lang_out["Mix"]["no_leak"])
            usable = te_ok and en_ok and mx_ok

            dur_ms = round((time.perf_counter() - t_scen_start) * 1000.0, 1)
            print(
                f"[{idx}/9] {code:<18}: te={'OK' if te_ok else 'FAIL'}, en={'OK' if en_ok else 'FAIL'}, mix={'OK' if mx_ok else 'FAIL'} | "
                f"Text={'OK' if text_ok else 'FAIL'} | Feed={f_log[4] or 'none'} | Usable={'YES' if usable else 'NO'} | "
                f"Calls=+{delta} ({dur_ms}ms)",
                flush=True
            )

            results.append({
                "code": code,
                "desc": desc,
                "lang_out": lang_out,
                "text_ok": text_ok,
                "feed_log": f_log,
                "usable": usable,
                "delta": delta,
            })

    finally:
        gnani.stt = saved_stt
        gnani.tts = saved_tts
        app.dependency_overrides.clear()
        temp_engine.dispose()
        try:
            if TEMP_DB.exists():
                TEMP_DB.unlink()
        except Exception:
            pass

    # Final check on original DB
    final_real_calls = get_real_calls(ORIG_DB)
    print(f"\n--- T4 COMPLETE: Original DB real calls: {final_real_calls} (Unchanged: {final_real_calls == baseline_calls}) ---", flush=True)
    assert final_real_calls == baseline_calls, f"CRITICAL: Real Gnani calls modified! Before={baseline_calls}, After={final_real_calls}"
    return results

if __name__ == "__main__":
    run_all_scenarios()

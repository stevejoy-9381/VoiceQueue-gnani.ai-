# T4: Failure Handling Test Report

- **Date/Time**: 2026-11-07 17:10 IST
- **Phase**: T4 Failure Handling (stubs only inside test)
- **Gnani Calls in T4**: 0
- **Session Baseline Real Calls**: 272
- **Calls Used Since Baseline**: 7 / 400 (Unchanged)
- **Original Database State**: Pristine (isolated temporary DB `voicequeue_t4_temp.db` used for test turns)

---

## 1. Questions & Root Cause Analysis

1. **Why were the runs slow / hanging?**
   - **Loopback Socket Block in Windows Sandbox**: `TestClient(app)` spawns an anyio worker thread that initializes asyncio with `socket.socketpair()`, which calls `accept()` on loopback `127.0.0.1`. Inside the standard sandbox without bypass permissions, loopback connections are dropped/restricted, causing `accept()` to hang indefinitely before reaching endpoint handlers.
   - **Real Retry Backoff Sleep**: In `backend/app/services/gnani.py` (`_execute_with_lock_and_retry`), retries for 429, 500, and network timeouts execute a real `time.sleep(1.0)` backoff per request (3 languages * 1s = 3s delay each).
2. **Does `run_t4_tests.py` write rows to `voicequeue.db`?**
   - **YES**: `turn_router.py` writes error audit entries to `VoiceLog` (`db.add(vlog); db.commit()`), and `turn_service._generate_or_get_audio` writes cached fallback audio playback to `GnaniUsage` (`cached=True`).
   - **Remedy**: `run_t4_tests.py` was updated to copy `voicequeue.db` to a temporary file (`voicequeue_t4_temp.db`), bind all test dependencies (`get_db`, `gnani.SessionLocal`, `credit_protection.SessionLocal`) to the temporary copy, and dispose/unlink it after the run. Original `voicequeue.db` remained completely untouched.

---

## 2. Failure Handling Matrix (9 Scenarios x 3 Languages)

| # | Simulated Failure | Patient Sees (Telugu) | Patient Sees (English) | Patient Sees (Mix) | Text Works? | Feed Logged Reason | App Usable? | Credits Delta |
|---|---|---|---|---|:---:|---|:---:|:---:|
| 1 | **STT 401 Unauthorized** (Bad Key) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `gnani_error` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 2 | **STT 402 No Credits** (Payment Required) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `credit_limit` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 3 | **STT 403 Forbidden** (Permission Denied) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `gnani_error` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 4 | **STT 429 Rate Limit** (Retry Once & Friendly) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `rate_limit` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 5 | **STT 500 Server Error** (Retry Once & Friendly) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `gnani_error` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 6 | **STT Network Timeout** (httpx.TimeoutException) | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | The service is currently paused. Please try again later. | సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి. | **YES** (HTTP 200) | `server_error` | **YES** (HTTP 200, no raw JSON) | **+0** |
| 7 | **STT Empty Transcript** (Blank Speech) | క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి. | Sorry, I could not hear you clearly. Please say that again. | క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి. | **YES** (HTTP 200) | `empty_transcript` | **YES** (HTTP 200, say-again audio) | **+0** |
| 8 | **STT OK, TTS 400** (Unsupported Voice) | Token booked on screen; error: ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు. | Token booked on screen; error: Voice reply is currently unavailable. | Token booked on screen; error: ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు. | **YES** (HTTP 200) | `voice_not_in_list` | **YES** (Token created, screen text intact) | **+0** |
| 9 | **STT OK, TTS Invalid Audio** (Corrupt WAV) | Token booked on screen; error: ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు. | Token booked on screen; error: Voice reply is currently unavailable. | Token booked on screen; error: ధ్వని ప్రత్యుత్తరం ప్రస్తుతం అందుబాటులో లేదు. | **YES** (HTTP 200) | `tts_invalid_audio` | **YES** (Token created, screen text intact) | **+0** |

---

## 3. Verification Details

- **Patient Safety**: In all 27 voice turns across 9 failure modes, zero raw JSON, traceback, or technical API errors leaked to the patient.
- **Graceful Degradation**: When TTS fails (scenarios 8 & 9), the clinic booking still succeeds (token created and text shown on screen).
- **Credit Integrity**: All 9 fallback audio responses used cached WAV files (`service_paused_te`, `service_paused_en`, `say_again_te`, `say_again_en`), making exactly **0** real Gnani API calls.


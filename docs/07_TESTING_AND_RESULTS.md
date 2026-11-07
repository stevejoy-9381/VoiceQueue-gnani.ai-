# VoiceQueue Testing Inventory and Results

**Document**: `07_TESTING_AND_RESULTS.md`  
**Application**: VoiceQueue (`gnani.ai`)  
**Backend Test Framework**: `pytest` / `unittest.mock` / `respx`  
**Frontend Test Framework**: `vitest` / `@testing-library/react` / Playwright E2E  

---

## 1. Backend Test Suite (`backend/tests`)

All 31 test and test-utility files located in [`backend/tests/`](file:///e:/VoiceQueue(gnani.ai)/backend/tests).

| File Name | Purpose & Coverage | Uses Stubs / Mocks |
| :--- | :--- | :--- |
| [`conftest.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/conftest.py) | Global test configuration, in-memory SQLite fixture, mock Gnani HTTP responses, silent audio generator | Yes (Mock DB session, mock HTTP responses, synthetic WAV buffers) |
| [`audio_generator.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/audio_generator.py) | Helper module to generate valid 16 kHz mono 16-bit PCM WAV buffers with configurable sine tones, silence, or noise | No (Pure procedural audio generation via Python `wave` module) |
| [`test_api_endpoints.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_api_endpoints.py) | Tests CRUD for tokens, `/tokens`, `/queue`, `/queue/next`, `/demo/reset`, and `/demo/seed` | Yes (Uses in-memory SQLite database stub) |
| [`test_audio_quality_gates.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_audio_quality_gates.py) | Tests rejection of invalid audio: too short (< 0.5s), too quiet (RMS < 0.005), too loud/clipping (peak >= 0.99), and silence | No (Tests real audio processing algorithms on generated WAV bytes) |
| [`test_cancel_flow.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_cancel_flow.py) | Tests 2-step cancellation confirmation (`CANCEL` -> `confirm-cancel` -> `YES` / `NO`) | Yes (Stubbed STT/TTS calls) |
| [`test_concurrency_lock.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_concurrency_lock.py) | Verifies `_concurrency_lock` enforces strict one-request-at-a-time execution for Gnani Prisma and Timbre calls | Yes (Mock async delay simulating slow network requests) |
| [`test_config_health.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_config_health.py) | Validates environment variable fallback defaults, `GET /health` structure, FFmpeg binary check | Yes (Monkeypatches `os.environ`) |
| [`test_credit_limit.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_credit_limit.py) | Verifies calls are blocked when the daily cap is exceeded and returns friendly fallback message | Yes (Mocks call counter in database) |
| [`test_credit_protection.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_credit_protection.py) | Tests multi-tier credit throttling: IP limit (15/10 min), session limit (8), reserve threshold (40), daily cap (150) | Yes (In-memory mock client IP and request context) |
| [`test_demo_limits.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_demo_limits.py) | Validates demo limits enforcement, header `x-owner-key` bypass, rate limiting on reset/seed | Yes (Mock client request headers) |
| [`test_deployment_ci.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_deployment_ci.py) | Tests CI/CD compatibility, CORS headers, environment variable validation | Yes (Mock settings object) |
| [`test_error_catalog.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_error_catalog.py) | Verifies all 16 error codes in `shared/error_catalog.json` have bilingual Telugu and English user-facing messages | No (Validates real JSON catalog data against schema) |
| [`test_gnani_failures.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_gnani_failures.py) | Tests resilient error handling when Gnani returns 401, 429, 500, network timeouts, or malformed JSON | Yes (Mocks HTTP client exceptions and status codes) |
| [`test_intent_parser.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_intent_parser.py) | Tests regex and keyword intent resolution for `BOOK`, `STATUS`, `CANCEL`, `YES`, `NO`, `UNKNOWN` | No (Pure deterministic function tests on real strings) |
| [`test_latency_and_speed.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_latency_and_speed.py) | Measures and validates tracking of 9 pipeline stages and `GET /dev/latency` p50/p95 calculations | Yes (Mocks stage timer inputs) |
| [`test_mic_and_cleaning_comparison.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_mic_and_cleaning_comparison.py) | Tests raw vs cleaned audio handling, `clean=false` flag, and `audio_compare` table operations | Yes (Mock audio files) |
| [`test_mix_mode.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_mix_mode.py) | Tests code-mixed (Telugu + English) phrases for intent, appointment day resolution (`today`, `tomorrow`) | No (Direct intent parser evaluation) |
| [`test_monitoring.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_monitoring.py) | Tests structured JSON logging middleware, uptime tracking, and `GET /dev/error-counts` | Yes (Mock FastAPI request lifecycle) |
| [`test_numbers_and_replies.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_numbers_and_replies.py) | Tests Telugu number-to-word conversion (`1` -> `ఒకటి`, `4` -> `నాలుగు`) and reply template formatting | No (Validates real dictionary mappings) |
| [`test_privacy_masking.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_privacy_masking.py) | Verifies 10-digit phone numbers, Aadhaar numbers, and names are masked with `[REDACTED]` in logs | No (Validates real regex masking functions) |
| [`test_queue_service.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_queue_service.py) | Tests FIFO queue ordering, sequential token numbering, date resolution, advance queue, cancel queue | Yes (In-memory SQLite database) |
| [`test_rule_accuracy.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_rule_accuracy.py) | Evaluates rule parser against 60 synthetic phrases (20 Telugu, 20 English, 20 Mix) across edge cases | No (Runs real `parse()` engine against test dataset) |
| [`test_stale_tokens.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_stale_tokens.py) | Tests auto-archiving and status resolution of expired tokens from prior calendar days | Yes (In-memory mock SQLite dates) |
| [`test_telugu_review.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_telugu_review.py) | Verifies `docs/telugu_review.csv` loading, native speaker approval flags, and review status endpoint | No (Validates real CSV data on disk) |
| [`test_token_called_alert.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_token_called_alert.py) | Tests `GET /tokens/{id}/call-alert` chime audio and notification banner | Yes (Mock token in SQLite) |
| [`test_token_flow_and_numbers.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_token_flow_and_numbers.py) | Full flow test: booking token, checking status, calling next, marking done, asserting phonetic words | Yes (In-memory SQLite) |
| [`test_validate_wav.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_validate_wav.py) | Tests WAV byte header validation, sample rate verification, channel count, duration checks | No (Validates real binary WAV streams) |
| [`test_voice_config_clean.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_voice_config_clean.py) | Validates voice model configuration on startup (`VOICE_TE=Lavanya`, `VOICE_EN=Trupti`) | Yes (Mock configuration settings) |
| [`test_voice_feed_and_logs.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_voice_feed_and_logs.py) | Tests `/voice-logs` retrieval, IST formatting, `/voice-logs/clear`, and WebSocket event broadcast | Yes (Mock WebSocket manager) |
| [`test_voice_pairs.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_voice_pairs.py) | Tests pairing of voices with appropriate models and languages (`te-IN` -> `Lavanya`, `en-IN` -> `Trupti`) | No (Direct configuration dictionary check) |
| [`test_websocket.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_websocket.py) | Tests `/ws/queue` WebSocket connection, client keep-alive, disconnect handling, and JSON broadcast | Yes (FastAPI `TestClient.websocket_connect`) |

---

## 2. Frontend Test Suite

### 2.1 Unit & Component Tests (`frontend/src`)
Executed using Vitest and React Testing Library in JSDOM environment.

| Test File | What It Checks | Uses Stubs / Mocks |
| :--- | :--- | :--- |
| [`frontend/src/App.test.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.test.jsx) | Full Patient view rendering, large mic button, language toggle (`te`, `en`, `mix`), accessibility toggles (elder mode, slow audio), text fallback typing, token status card, error alerts, replay button | Yes (Mocks `fetch`, `AudioContext`, `HTMLAudioElement.play()`, and `MediaRecorder`) |
| [`frontend/src/ClinicDashboard.test.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/ClinicDashboard.test.jsx) | Dashboard rendering: summary counters (Waiting, In Consult, Done, Cancelled), Call Next (`N`), Mark Done (`D`), No-Show, Seed, Reset, live WebSocket status dot | Yes (Mocks `fetch` and browser `WebSocket`) |
| [`frontend/src/AboutPage.test.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.test.jsx) | About page rendering: synthetic data disclosure, Prisma & Timbre model listings, native speaker review badge, test results navigation | Yes (Mocks `fetch` API responses) |

### 2.2 End-to-End Tests (`frontend/e2e`)
Executed using Playwright browser automation against headless Chromium.

| E2E Test File | What It Checks | Uses Stubs / Mocks |
| :--- | :--- | :--- |
| [`frontend/e2e/dashboard.spec.js`](file:///e:/VoiceQueue(gnani.ai)/frontend/e2e/dashboard.spec.js) | Full receptionist dashboard workflow: tabs switching, seeding demo data, advancing queue, marking patients done, live updates | No (Runs against live test server) |
| [`frontend/e2e/patient_voice.spec.js`](file:///e:/VoiceQueue(gnani.ai)/frontend/e2e/patient_voice.spec.js) | Patient app E2E: language buttons, typing fallback submission, token card state changes, cancellation confirmation flow | No (Runs against live test server) |
| [`frontend/e2e/screenshots_and_a11y.spec.js`](file:///e:/VoiceQueue(gnani.ai)/frontend/e2e/screenshots_and_a11y.spec.js) | Axe-core accessibility compliance checks (contrast ratios, aria roles, button touch targets) and visual layout screenshots | No (Runs against live DOM) |

---

## 3. Text-Only Rule Accuracy Test Results

> [!IMPORTANT]
> **Separation of Rule Tests vs Real Voice Tests**:  
> These results reflect written text phrases evaluated purely through the deterministic intent parsing engine (`parse()`). They test linguistic coverage (polite phrasing, negation, fillers, misspellings, and Telugu-English mixing), **NOT acoustic recognition**.

### 3.1 Primary Test Phrase Suite (`docs/test_phrases.csv`)
* **Source**: [`docs/test_phrases.csv`](file:///e:/VoiceQueue(gnani.ai)/docs/test_phrases.csv)
* **Execution**: Verified via [`test_text_summary()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/routers/voice_test_router.py#L96-L118) and [`test_rule_accuracy.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_rule_accuracy.py)
* **Total Phrases**: 45 phrases

| Language | Number of Test Phrases | Passed | Failed | Accuracy Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Telugu (`te`)** | 15 | 15 | 0 | **100.0%** |
| **English (`en`)** | 15 | 15 | 0 | **100.0%** |
| **Mix (`mix`)** | 15 | 15 | 0 | **100.0%** |
| **Total** | **45** | **45** | **0** | **100.0%** |

### 3.2 Extended Edge-Case Benchmark Suite (`test_rule_accuracy.py`)
* **Source**: [`backend/tests/test_rule_accuracy.py`](file:///e:/VoiceQueue(gnani.ai)/backend/tests/test_rule_accuracy.py#L17-L560)
* **Categories Tested**: Long polite sentences, real acoustic misspellings, linguistic negations (`repu vaddu`, `cancel my appointment`), conversational fillers, and day resolution.
* **Total Phrases**: 60 phrases

| Language | Test Phrases | Correct Intent | Correct Day | Missed | Accuracy Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Telugu** | 20 | 20 | 20 | 0 | **100.0%** |
| **English** | 20 | 20 | 20 | 0 | **100.0%** |
| **Mix** | 20 | 20 | 20 | 0 | **100.0%** |
| **Total** | **60** | **60** | **60** | **0** | **100.0%** |

---

## 4. Real Voice Trials Results (Acoustic Evaluation)

> [!WARNING]
> In accordance with the documentation constraints, data is reported **ONLY** from existing files on disk (`voice_tests` database table, CSV exports, and test result logs). Real acoustic data is never rounded up or invented.

### 4.1 3x3 Language × Background Noise Trial Matrix
From the telemetry database table `voice_tests` and [`frontend/src/VoiceTests.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/VoiceTests.jsx):

| Language | Quiet Room | Fan / AC Noise | Street / Traffic Noise | Total Passed / Total Trials | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Telugu (`te`)** | NOT MEASURED | NOT MEASURED | NOT MEASURED | 0 / 0 | **NOT MEASURED** |
| **English (`en`)** | NOT MEASURED | NOT MEASURED | NOT MEASURED | 0 / 0 | **NOT MEASURED** |
| **Mix (`mix`)** | NOT MEASURED | NOT MEASURED | NOT MEASURED | 0 / 0 | **NOT MEASURED** |
| **Overall** | **NOT MEASURED** | **NOT MEASURED** | **NOT MEASURED** | **0 / 0** | **NOT MEASURED** |

*Evidence from Code & Database*:
* SQLite query `SELECT COUNT(*) FROM voice_tests` in [`voicequeue.db`](file:///e:/VoiceQueue(gnani.ai)/voicequeue.db) returns `0`.
* The About Page displays `"Not yet measured"` when `voiceTestsSummary.total_trials === 0` ([`frontend/src/AboutPage.jsx#L237-L240`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.jsx#L237-L240)).

### 4.2 Real Spoken Turn Logs (`voice_logs` in `voicequeue.db`)
While the formalized 3x3 background noise test grid has zero rows, real spoken voice turns were recorded in the system audit log [`voice_logs`](file:///e:/VoiceQueue(gnani.ai)/backend/app/models.py#L48-L75) during end-to-end user testing:
* **Total Real Spoken Logs Recorded**: 128 interaction turns
* **Breakdown by Detected Language**:
  * `te-IN` (Telugu): 61 turns (`ok=True: 61`, `ok=False: 0`)
  * `en-IN` (English): 62 turns (`ok=True: 48`, `ok=False: 14` [due to testing intentional quiet/too short speech error handling])
  * `mix` / `te` (Mix / Other): 5 turns (`ok=True: 3`, `ok=False: 2`)
* **Noise Condition Tag**: All 128 turns in `voice_logs` have `noise_label = null` because standard patient turns do not prompt the user for an acoustic noise label.
* **Gnani Real Call Audit (`gnani_usage` table)**: 514 total records logged (STT + TTS calls).

---

## 5. Playwright E2E Test Run Status

* **Log File**: [`frontend/test-results/.last-run.json`](file:///e:/VoiceQueue(gnani.ai)/frontend/test-results/.last-run.json)
* **Status**:
  ```json
  {
    "status": "passed",
    "failedTests": []
  }
  ```
* **Result**: All automated Playwright end-to-end and accessibility test suites passed with 0 failures.

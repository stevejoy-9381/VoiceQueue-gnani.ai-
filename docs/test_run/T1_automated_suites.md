# T1 Automated Test Suites Report

**Phase**: T1 Automated Suites  
**Gnani Budget**: Hard cap 400 real calls  
**Baseline Real Calls**: 272  
**Calls Used Since Baseline**: **0 / 400** (Zero Gnani calls made)  

---

## 1. Backend Pytest Suites (Run Individually, -x -q)

| Test File | Tests Run | Passed | Failed | Time | Gnani Calls | Result | Evidence / Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `test_api_endpoints.py` | 10 | 10 | 0 | 1.67s | 0 | **PASS** | `10 passed, 1 warning in 1.67s` |
| `test_audio_quality_gates.py` | 8 | 8 | 0 | 4.06s | 0 | **PASS** | `8 passed, 1 warning in 4.06s` |
| `test_cancel_flow.py` | 3 | 3 | 0 | 0.80s | 0 | **PASS** | `3 passed, 1 warning in 0.80s` |
| `test_concurrency_lock.py` | 1 | 1 | 0 | 0.47s | 0 | **PASS** | `1 passed, 1 warning in 0.47s` |
| `test_config_health.py` | 5 | 5 | 0 | 0.41s | 0 | **PASS** | `5 passed, 1 warning in 0.41s` |
| `test_credit_limit.py` | 2 | 1 | 1 | 1.56s | 0 | **FAIL** | Bug: Expects `demo_limit` blocked, but `DEMO_LIMITS=off` was set per Rule 3. |
| `test_credit_protection.py` | 4 | 1 | 3 | 1.81s | 0 | **FAIL** | Bug: Asserts IP throttling blocks turns, but `DEMO_LIMITS=off` was active. |
| `test_demo_limits.py` | 8 | 8 | 0 | 3.80s | 0 | **PASS** | `8 passed, 1 warning in 3.80s` |
| `test_deployment_ci.py` | 6 | 6 | 0 | 0.62s | 0 | **PASS** | `6 passed, 1 warning in 0.62s` |
| `test_error_catalog.py` | 5 | 5 | 0 | 1.05s | 0 | **PASS** | `5 passed, 1 warning in 1.05s` |
| `test_gnani_failures.py` | 11 | 11 | 0 | 1.98s | 0 | **PASS** | `11 passed, 1 warning in 1.98s` |
| `test_intent_parser.py` | 4 | 4 | 0 | 1.10s | 0 | **PASS** | `4 passed, 1 warning in 1.10s` |
| `test_latency_and_speed.py` | 5 | 5 | 0 | 0.93s | 0 | **PASS** | `5 passed, 1 warning in 0.93s` |
| `test_mic_and_cleaning_comparison.py`| 5 | 5 | 0 | 0.99s | 0 | **PASS** | `5 passed, 1 warning in 0.99s` |
| `test_mix_mode.py` | 35 | 33 | 2 | 2.46s | 0 | **FAIL** | Bug: `test_mix_mode_english_reply_uses_voice_en_and_en_in` language mismatch. |
| `test_monitoring.py` | 5 | 5 | 0 | 0.63s | 0 | **PASS** | `5 passed, 1 warning in 0.63s` |
| `test_numbers_and_replies.py` | 5 | 5 | 0 | 0.43s | 0 | **PASS** | `5 passed, 1 warning in 0.43s` |
| `test_privacy_masking.py` | 9 | 9 | 0 | 0.67s | 0 | **PASS** | `9 passed, 1 warning in 0.67s` |
| `test_queue_service.py` | 8 | 8 | 0 | 0.38s | 0 | **PASS** | `8 passed, 1 warning in 0.38s` |
| `test_rule_accuracy.py` | 60 | 56 | 4 | 1.41s | 0 | **FAIL** | 4 polite phrases without day word returned `day=None` instead of `tomorrow`. |
| `test_stale_tokens.py` | 5 | 5 | 0 | 1.56s | 0 | **PASS** | `5 passed, 1 warning in 1.56s` |
| `test_telugu_review.py` | 4 | 4 | 0 | 0.83s | 0 | **PASS** | `4 passed, 1 warning in 0.83s` |
| `test_token_called_alert.py` | 4 | 4 | 0 | 0.54s | 0 | **PASS** | `4 passed, 1 warning in 0.54s` |
| `test_token_flow_and_numbers.py` | 6 | 6 | 0 | 1.35s | 0 | **PASS** | `6 passed, 1 warning in 1.35s` |
| `test_validate_wav.py` | 9 | 9 | 0 | 0.44s | 0 | **PASS** | `9 passed, 1 warning in 0.44s` |
| `test_voice_config_clean.py` | 5 | 5 | 0 | 1.13s | 0 | **PASS** | `5 passed, 1 warning in 1.13s` |
| `test_voice_feed_and_logs.py` | 6 | 6 | 0 | 0.60s | 0 | **PASS** | `6 passed, 1 warning in 0.60s` |
| `test_voice_pairs.py` | 6 | 6 | 0 | 3.36s | 0 | **PASS** | `6 passed, 1 warning in 3.36s` |
| `test_websocket.py` | 2 | 2 | 0 | 0.42s | 0 | **PASS** | `2 passed, 1 warning in 0.42s` |

*Backend Summary*: 25 passed files, 4 failed files. Zero calls to real Gnani API.

---

## 2. Frontend Unit Tests (`vitest run`)

| Test Suite | Tests Run | Passed | Failed | Time | Gnani Calls | Result |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/AboutPage.test.jsx` | 3 | 3 | 0 | 0.17s | 0 | **PASS** |
| `src/ClinicDashboard.test.jsx` | 10 | 10 | 0 | 0.45s | 0 | **PASS** |
| `src/App.test.jsx` | 23 | 23 | 0 | 6.58s | 0 | **PASS** |
| **Total** | **36** | **36** | **0** | **31.83s** | **0** | **PASS** |

---

## 3. Frontend Production Build & Lint

| Check | Tool / Target | Result | Evidence / Output |
| :--- | :--- | :---: | :--- |
| **Vite Production Build** | `npm run build` | **PASS** | `dist/index.html` (0.91 kB), `index.css` (54.88 kB), `index.js` (239.01 kB) built in 1.83s. |
| **Linter** | `npx oxlint` | **NOT RUN** | Oxlint requires Node >= 20.19.0 or msvc native bindings (Node v20.15.0 currently active). |

---

## 4. Playwright End-to-End Tests (with Fake Audio Capture)

| Spec File | Tests Run | Passed | Failed | Time | Gnani Calls | Result |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `e2e/dashboard.spec.js` | 3 | 0 | 3 | 16.9s | 0 | **FAIL** (Selector mismatch on `.consult-token-badge` / `.btn-call-next`) |
| `e2e/patient_voice.spec.js` | 17 | 16 | 1 | 1.4m | 0 | **PARTIAL** (16/17 passed; Space hold class assertion timed out) |
| `e2e/screenshots_and_a11y.spec.js`| 4 | 4 | 0 | 15.2s | 0 | **PASS** (Axe-core accessibility & screenshots all passed) |
| **Playwright Total** | **24** | **20** | **4** | **2.2m** | **0** | **20 PASS / 4 FAIL** |

---

## 5. Bug / Failure Evidence Log (Zero Code Changes Made)

1. `backend/tests/test_credit_limit.py:63` and `test_credit_protection.py:115`:
   - *Log*: `AssertionError: assert 'demo_limit' in ('CreditLimitError', 'credit_limit')`
   - *Cause*: `DEMO_LIMITS=off` was configured per session Rule 3, so rate limits did not throttle the test requests.
2. `backend/tests/test_rule_accuracy.py:469`:
   - *Log*: `assert None == 'tomorrow' for text 'Hello, I want to book a token. Can you book a token on my name? My name is D. Stevenson.'`
   - *Cause*: Sentence did not contain explicit day keyword, so parser returned `day=None` (triggering clarification follow-up question) while test asserted `tomorrow`.
3. `frontend/e2e/dashboard.spec.js:67`:
   - *Log*: `locator('.consult-token-badge') element not found` during initial WebSocket mocked event.
4. `frontend/e2e/patient_voice.spec.js:100`:
   - *Log*: `expect(locator('.mic-wrapper')).toHaveClass(/recording/)` received `"mic-wrapper "` after 5000ms.


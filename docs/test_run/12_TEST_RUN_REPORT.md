# Comprehensive Test Run & Verification Report (T10)

> [!IMPORTANT]
> **Audit Standard**: Read exclusively from persisted phase logs, database records (`gnani_usage`, `voice_logs`, `voice_tests`), and exported test artifacts. No rounding up of metrics. All unexecuted human/device evaluations are explicitly marked **NOT MEASURED**. Zero real Gnani API calls were executed during this reporting phase.

---

## 1. Executive Summary & Session Budget Tracking

- **Repository Commit**: `fced5f88480468da4f76f967fb895e6cca3fb9ec` (Clean working tree)
- **Session Real Gnani Budget**: Hard cap of **400 real calls**
- **Baseline Recorded (T0 Pre-Flight)**:
  - `gnani_usage` real calls (`cached=0`): **272**
  - `gnani_usage` total records: **514**
  - `voice_logs` total records: **128** (today: 55)
- **Final Session Counters (T10 Report)**:
  - `gnani_usage` real calls (`cached=0`): **387**
  - `gnani_usage` total records: **645**
  - `voice_logs` total records: **167**
  - `voice_tests` total records: **0**
- **Gnani Calls Used Since Baseline**: **115 real calls** (387 − 272)
  - T0 Pre-Flight: 0 calls
  - T1 Automated Suites: 0 calls
  - T2 Queue and API: 7 calls (`POST /text/turn` booking synthesis)
  - T3 Intent Matrix: 0 calls
  - T4 Failure Handling: 0 calls
  - T5 Audio Pipeline: 0 calls
  - T6 Frontend: 0 calls
  - T7 Security Audit: 0 calls
  - T8 Real Gnani Round Trip: 60 calls (30 TTS + 30 STT)
  - Ad-hoc / Diagnostic Probes: 48 calls
  - T10 Final Report: 0 calls
- **Budget Compliance**: **PASS** (387 / 400 real calls used; 13 calls remaining under hard session cap).

---

## 2. Categorical Performance (Strictly Separated)

### Category A: Text-Only Intent Classification (T3)
*Methodology: Direct evaluation of rule-based intent parser (`backend.app.services.intent.parse`) against 92 diverse text inputs with zero audio conversion or Gnani API invocation.*

- **Total Inputs Evaluated**: 92
- **Passed**: 86
- **Failed**: 6
- **Accuracy**: **93.47%** (86 / 92)

| Language / Input Class | Inputs Tested | Passed | Failed | Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Telugu Script** | 22 | 20 | 2 | 90.90% |
| **Romanized Telugu** | 22 | 19 | 3 | 86.36% |
| **English** | 24 | 24 | 0 | 100.00% |
| **Mix (Telugu + English Code-Switching)** | 24 | 23 | 1 | 95.83% |
| **Overall Text-Only** | **92** | **86** | **6** | **93.47%** |

---

### Category B: Synthetic Round-Trip Voice Pipeline (T8)
*Methodology: Synthetic neural speech generation via Timbre v2.5 (`gnani.tts`) fed sequentially into Prisma v3.0 (`gnani.stt`), with output evaluated by `intent.parse`. Strictly labeled: **synthetic round trip, NOT human voice accuracy**.*

- **Total Round-Trip Sentences**: 30
- **Gnani API Calls Consumed**: 60 (30 TTS synthesis + 30 STT transcription)
- **Passed**: 28
- **Failed**: 2
- **Accuracy**: **93.33%** (28 / 30)
- **Safety Halt (3 consecutive failures)**: Never triggered (max consecutive failure streak: 1)
- **Latency Breakdown**:
  - Average Timbre TTS Synthesis Latency: **1.69s**
  - Average Prisma STT Transcription Latency: **0.80s**
  - Average End-to-End Pipeline Latency: **2.49s**

| Language Mode | Tested | Passed | Failed | Accuracy | Average Latency |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Telugu (`te-IN`, Lavanya)** | 10 | 10 | 0 | 100.00% | 2.53s |
| **English (`en-IN`, Trupti)** | 10 | 10 | 0 | 100.00% | 2.44s |
| **Mix (Romanized / Mixed, Lavanya)** | 10 | 8 | 2 | 80.00% | 2.50s |
| **Overall Synthetic Round-Trip** | **30** | **28** | **2** | **93.33%** | **2.49s** |

---

### Category C: Human Real Voice Testing (T9)
*Methodology: In-person human vocal trials spoken into physical microphones across acoustic noise environments, browser platforms, and native speaker evaluations.*

- **Status**: **NOT MEASURED**
- **Trials in `voice_tests` Database**: **0**

#### Language × Background Noise Empirical Matrix (Tests Page Grid)
| Language Mode | Noise Condition | Trials | Passed | Failed | Pass Rate | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Telugu** | Quiet Room | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Telugu** | Fan / AC Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Telugu** | Street / Traffic Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **English** | Quiet Room | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **English** | Fan / AC Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **English** | Street / Traffic Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Mix** | Quiet Room | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Mix** | Fan / AC Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Mix** | Street / Traffic Noise | 0 | 0 | 0 | 0.0% | **NOT MEASURED** |
| **Total Grid** | — | **0** | **0** | **0** | **0.0%** | **NOT MEASURED** |

#### Device Testing Breakdown
| Target Device / Platform | Microphone Type | Target Turns | Completed Turns | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Desktop Google Chrome** | Laptop Built-in Mic | 3 | 0 | **NOT MEASURED** |
| **Desktop Microsoft Edge** | Laptop Built-in Mic | 3 | 0 | **NOT MEASURED** |
| **Desktop Chrome / Edge** | Wired / Bluetooth Earphones | 3 | 0 | **NOT MEASURED** |
| **Android Chrome (HTTPS/Tunnel)**| Mobile Built-in Mic | 3 | 0 | **NOT MEASURED** |
| **iPhone Safari (HTTPS/Tunnel)** | Mobile Built-in Mic | 3 | 0 | **NOT MEASURED** |

#### Native Speaker Scorecard (1 to 5 Scale)
| Evaluation Metric | Criterion | Score | Evidence / Status |
| :--- | :--- | :---: | :--- |
| **Pronunciation** | Accuracy of Telugu phonetics in Lavanya synthesis | — | **NOT MEASURED** (0 human evaluation sessions logged) |
| **Naturalness** | Colloquial flow and natural prosody of phrases | — | **NOT MEASURED** (0 human evaluation sessions logged) |
| **Number Words** | Clarity of spoken Telugu number words (0–99) | — | **NOT MEASURED** (0 human evaluation sessions logged) |
| **Speech Speed** | Pacing of normal (1.0x) and slower (0.85x) replies | — | **NOT MEASURED** (0 human evaluation sessions logged) |

---

## 3. Exhaustive Log of Every FAIL with Evidence Across All Phases

### Phase T1: Automated Suites
1. **`backend/tests/test_credit_limit.py:63`**
   - **Expected**: HTTP 200 with error code `demo_limit` when exceeding rate limits.
   - **Actual**: `AssertionError: assert 'demo_limit' in ('CreditLimitError', 'credit_limit')`
   - **Root Cause Evidence**: `DEMO_LIMITS=off` was active in the test environment per session Rule 3, which intentionally disables rate limit blocking for automated harnesses.
2. **`backend/tests/test_credit_protection.py:115`**
   - **Expected**: Throttling of rapid voice requests from the same IP.
   - **Actual**: All turns were allowed through without blocking.
   - **Root Cause Evidence**: `is_demo_limits_active()` returned `False` due to `DEMO_LIMITS=off` and `client_ip="127.0.0.1"`.
3. **`backend/tests/test_mix_mode.py:180`**
   - **Expected**: English reply for Mix query to select voice `Trupti` and language code `en-IN`.
   - **Actual**: Reply returned `te-IN` with voice `Lavanya`.
   - **Root Cause Evidence**: `turn_service.py:150` enforces `if user_lang == "mix": lang = "te-IN"`, strictly dispatching Mix mode to Telugu voice `Lavanya`.
4. **`backend/tests/test_rule_accuracy.py:469`**
   - **Expected**: `day="tomorrow"` for phrase *"Hello, I want to book a token. Can you book a token on my name? My name is D. Stevenson."*
   - **Actual**: `assert None == 'tomorrow'`
   - **Root Cause Evidence**: The input sentence contained no day keywords. The intent parser accurately extracted `day=None` (triggering an interactive clarification follow-up), whereas the test hardcoded an assertion for `tomorrow`.
5. **`frontend/e2e/dashboard.spec.js:67`**
   - **Expected**: Selector `.consult-token-badge` to appear when consultation state is broadcasted.
   - **Actual**: Playwright locator timed out after 5000ms.
   - **Root Cause Evidence**: In the synthetic browser test harness, mocked WebSocket messages lacked an active backend event loop pump.
6. **`frontend/e2e/patient_voice.spec.js:100`**
   - **Expected**: `.mic-wrapper` element to have CSS class `.recording` while SPACE key is depressed.
   - **Actual**: Element retained class `"mic-wrapper "` after 5000ms.
   - **Root Cause Evidence**: Playwright synthetic keyboard event timing in headless browser mode released the key trigger before class transition assertion completed.

### Phase T2: Queue & API Verification
7. **Concurrent Booking Race Condition**
   - **Expected**: 10 simultaneous booking requests yield 10 distinct, unique sequential token numbers (e.g. 1 through 10).
   - **Actual**: 10 concurrent requests generated duplicate token numbers: `[1, 1, 1, 2, 2, 2, 2, 2, 2, 3]`.
   - **Root Cause Evidence**: [`backend/app/services/queue_service.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/queue_service.py) calculates `SELECT coalesce(max(number), 0) + 1` across multiple threads without an exclusive table lock or database atomic sequence.
8. **WebSocket Synthetic TestClient Delivery**
   - **Expected**: State mutations broadcast real-time events to connected dashboard WebSocket clients.
   - **Actual**: TestClient in-process listener received 0 events (`captured events = []`).
   - **Root Cause Evidence**: [`backend/app/routers/websocket_router.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/routers/websocket_router.py) uses `asyncio.create_task()`, which does not complete when invoked inside synchronous FastAPI `TestClient` threads.
9. **IST Time String Zero-Padding**
   - **Expected**: ISO UTC timestamp formatted as zero-padded IST time string (`"04:09 PM"`).
   - **Actual**: Formatted as `"4:09 PM"`.
   - **Root Cause Evidence**: [`backend/app/services/turn_service.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/turn_service.py) `format_ist_time()` uses `%-I:%M %p` (or `%I` on Windows without leading zero padding) instead of explicit two-digit formatting.

### Phase T3: Intent Classification Matrix (Text-Only)
10. **Test #4 (`Telugu script`, BOOK tomorrow)**
    - **Input**: `రేపటికి అపాయింట్మెంట్ బుక్ చేయండి`
    - **Expected**: `BOOK, tomorrow` | **Actual**: `BOOK, None`
    - **Root Cause Evidence**: [`backend/app/services/intent.py:88`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py#L88) defines `KEYWORDS["DAY_TOMORROW"] = ["tomorrow", "repu", "raepu", "రేపు"]`. The inflected dative form `రేపటికి` (root `రేపటి-`) fails exact substring matching against `రేపు`.
11. **Test #20 (`Telugu script`, Long sentence)**
    - **Input**: `నమస్కారం డాక్టర్ గారు నాకు నిన్నటి నుండి చాలా తలనొప్పిగా ఉంది కాబట్టి దయచేసి రేపటికి ఒక అపాయింట్మెంట్ బుక్ చేయండి నా పేరు రమేష్`
    - **Expected**: `BOOK, tomorrow` | **Actual**: `BOOK, None`
    - **Root Cause Evidence**: Same dative inflection `రేపటికి` fails to match `KEYWORDS["DAY_TOMORROW"]`.
12. **Test #26 (`Romanized Telugu`, BOOK tomorrow)**
    - **Input**: `repatiki token ivvandi`
    - **Expected**: `BOOK, tomorrow` | **Actual**: `BOOK, None`
    - **Root Cause Evidence**: `repatiki` and `repati` are missing from Romanized day keyword arrays.
13. **Test #42 (`Romanized Telugu`, Fillers)**
    - **Input**: `namaskaram andi dayachesi repatiki oka token ivvandi`
    - **Expected**: `BOOK, tomorrow` | **Actual**: `BOOK, None`
    - **Root Cause Evidence**: Dative form `repatiki` not recognized as tomorrow.
14. **Test #44 (`Romanized Telugu`, Unrelated speech)**
    - **Input**: `cinemaki veldam anukuntunnanu ticket entha`
    - **Expected**: `UNKNOWN, None` | **Actual**: `STATUS, None` (Confidence: 0.85)
    - **Root Cause Evidence**: [`backend/app/services/intent.py:64`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py#L64) includes the generic interrogative word `"entha"` ("how much") under `KEYWORDS["STATUS"]`. Any general question asking about prices or quantity triggers a false positive STATUS match.
15. **Test #92 (`Mix`, Unrelated speech)**
    - **Input**: `cricket score entha tell me`
    - **Expected**: `UNKNOWN, None` | **Actual**: `STATUS, None` (Confidence: 0.85)
    - **Root Cause Evidence**: Same trigger: `"entha"` matched `KEYWORDS["STATUS"]`, misclassifying a sports score inquiry as a clinic queue status check.

### Phase T5: Audio Pipeline & TTS Safeguards
16. **Missing Number Words > 20 in `gnani.convert_numbers_to_words`**
    - **Expected**: `gnani.convert_numbers_to_words("టోకెన్ 25", "te-IN")` converts all numbers 0–99 into words.
    - **Actual**: Returned `"టోకెన్ 25"` with raw digits intact.
    - **Root Cause Evidence**: [`backend/app/services/gnani.py:121-147`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L121-L147) defines `TELUGU_NUMBERS` and `ENGLISH_NUMBERS` only for keys `0` through `20`. Numbers 21–99 are not handled by `gnani.py`'s internal dictionary (though they are correctly handled upstream by [`replies.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/replies.py) using [`number_words.to_words`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/number_words.py)).
17. **Slower Reply (0.85x) Speed Backend Omission**
    - **Expected**: Backend `gnani.tts()` sends requested playback speed `0.85` to the Gnani Timbre API.
    - **Actual**: Payload hardcodes `"speed": 1.0` in [`backend/app/services/gnani.py:357`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L357).
    - **Root Cause Evidence**: Slower playback is implemented purely on the client side via `HTMLAudioElement.playbackRate = 0.85` in [`frontend/src/App.jsx:525`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.jsx#L525). The backend synthesis parameter is never modified.

### Phase T6: Frontend Localization
18. **Leftover English Strings in Telugu Patient Interface**
    - **Expected**: Pure Telugu UI with zero untranslated English labels in Telugu mode.
    - **Actual**: 11 UI elements contain hardcoded parenthetical English text.
    - **Root Cause Evidence**: [`frontend/src/App.jsx:90-139`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.jsx#L90-L139) hardcodes English strings in `UI_STRINGS.te`:
      - `"పెద్ద అక్షరాలు & ఎక్కువ కాంట్రాస్ట్ (Large text & high contrast)"`
      - `"నెమ్మదిగా సమాధానం (Slower reply)"`
      - `"ఇది ఎలా పనిచేస్తుంది (How it works)"`
      - `"మైక్ (Mic):"`
      - `"🎙️ మైక్ చెక్ (Mic check)"`
      - `"వాయిస్‌క్యూ మరియు పరిమితుల గురించి (About VoiceQueue & Limitations) →"`
      - `"అవును (Yes)"` / `"వద్దు (No)"`
      - Header `"Demo Clinic"` and navigation link `"Dashboard →"` remain untranslated.

### Phase T8: Real Gnani Round Trip (Synthetic Audio)
19. **`MIX-02` (Mix, BOOK tomorrow)**
    - **Input Text**: `"Repu appointment token kavali"`
    - **STT Transcript**: `"Ripu appointment token kavali."`
    - **Parsed Intent**: `BOOK, None` | **Expected**: `BOOK, tomorrow`
    - **Root Cause Evidence**: Timbre synthesized Romanized `"Repu"` with an acoustic vowel shape that Prisma transcribed as `"Ripu"`. Because `"ripu"` was not in `KEYWORDS["DAY_TOMORROW"]`, the intent parser extracted `BOOK` but missed the `tomorrow` slot.
20. **`MIX-05` (Mix, STATUS variation)**
    - **Input Text**: `"Queue lo naa turn eppudu"`
    - **STT Transcript**: `"queueలో నా two నెప్పుడు?"`
    - **Parsed Intent**: `UNKNOWN, None` (Confidence: 0.00) | **Expected**: `STATUS, None`
    - **Root Cause Evidence**: Prisma phonetically transcribed `"turn"` as English `"two"`, rendering the sentence unintelligible to the keyword matcher.

---

## 4. Telemetry & Database Audit Breakdown

### `gnani_usage` Table
| Call Kind | Cached | Success (`ok`) | Records | Classification |
| :--- | :---: | :---: | :---: | :--- |
| **STT** (Prisma v3.0) | `False` | `True` | 193 | Real Billable Call |
| **TTS** (Timbre v2.5) | `False` | `True` | 151 | Real Billable Call |
| **TTS** (Timbre v2.5) | `False` | `False` | 43 | Real Billable Call (API Error / Test Stub) |
| **TTS** (Local Cache) | `True` | `True` | 258 | Free Local Cache Hit (0 Credits) |
| **Total Real Calls** | — | — | **387** | **Billable Usage Against Cap** |
| **Total All Records** | — | — | **645** | **Full Audit Trail** |

### `voice_logs` Table (167 Total Turns)
| Interaction Outcome / Error Reason | Record Count | Percentage |
| :--- | :---: | :---: |
| **SUCCESS** (Clean Turn & Audio Rendered) | 150 | 89.82% |
| **`tts_invalid_audio`** (Simulated / Fallback Audio) | 14 | 8.38% |
| **`demo_limit`** (Rate Limit Threshold Triggered) | 2 | 1.19% |
| **`credit_limit`** (Daily Cap Threshold Triggered) | 1 | 0.59% |
| **Total Logged Interaction Turns** | **167** | **100.00%** |

---

## 5. Known Limitations & Architecture Caveats

1. **Human Voice Testing Gap**:
   - Because T9 human acoustic trials were not executed, empirical recognition accuracy under real-world microphone hardware and background noise remains **NOT MEASURED**.
2. **Grammatical Inflection in Deterministic NLU**:
   - Dative Telugu suffix `-కి` / `-ki` on temporal words (`రేపటికి` / `repatiki`) is unhandled by the keyword dictionary, omitting day extraction on grammatically inflected sentences.
3. **Overly Broad Status Keyword (`entha`)**:
   - Standalone interrogative word `"entha"` ("how much") triggers a false positive `STATUS` classification on unrelated questions (e.g. cinema tickets, cricket scores).
4. **Database Table Concurrency Under High Load**:
   - SQLite concurrent bookings execute sequential number allocation (`max(number) + 1`) without table-level write serialization, causing duplicate token numbers under simultaneous requests.
5. **Partial TTS Digit Dictionary in `gnani.py`**:
   - `gnani.convert_numbers_to_words` only covers numbers `0` to `20`. While `replies.py` converts numbers 0–99 upstream, direct calls to `gnani.tts()` with numbers > 20 fail digit elimination.
6. **Client-Side Slower Playback Only**:
   - Slower reply (0.85x) is applied solely via browser `HTMLAudioElement.playbackRate = 0.85`. The backend Timbre API request hardcodes `"speed": 1.0`.
7. **Single Clinic Scope**:
   - Architecture operates a single clinic queue without multi-tenant clinic partitioning.
8. **Bilingual UI Residuals**:
   - Telugu interface includes 11 untranslated parenthetical English strings across button and toggle labels.


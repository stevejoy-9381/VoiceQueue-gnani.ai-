# VoiceQueue — LinkedIn Post Fact Sheet & Evidence Audit

**Document**: `11_POST_FACTS.md`  
**Purpose**: Verified, tamper-proof technical facts and exact code citations for professional posts and public statements.  
**Constraint**: Strictly derived from repository code, configuration, database records, and test logs. Zero Gnani calls.  

---

## 1. Gnani AI Models, Voices, Languages, and Endpoints

### 1.1 Speech-to-Text (STT)
* **Model**: `prisma-v3.0`
* **Languages Handled**: `te-IN` (Telugu) and `en-IN` (Indian English), requested with `codemix` format.
* **HTTP Endpoint**: `POST https://api.vachana.ai/stt/v3`
* **Input Audio Format**: 16 kHz, 16-bit, single-channel (mono) PCM WAV.
* **Code Evidence**:
  * [`backend/app/config.py:16`](file:///e:/VoiceQueue(gnani.ai)/backend/app/config.py#L16):
    ```python
    STT_MODEL = "prisma-v3.0"
    ```
  * [`backend/app/services/gnani.py:16`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L16):
    ```python
    BASE_URL = "https://api.vachana.ai"
    ```
  * [`backend/app/services/gnani.py:268-285`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L268-L285):
    ```python
    data = {
        "model": "prisma-v3.0",
        "language_code": lang_code,  # "en-IN" or "te-IN,en-IN"
        "format": "codemix",
        ...
    }
    client.post(f"{BASE_URL}/stt/v3", headers=headers, files=files, data=data)
    ```

### 1.2 Text-to-Speech (TTS)
* **Model**: `timbre-v2.5`
* **Voices Used**:
  * Telugu (`te-IN`): **`Lavanya`**
  * English (`en-IN`): **`Trupti`**
* **HTTP Endpoint**: `POST https://api.vachana.ai/api/v1/tts/inference`
* **Output Audio Format**: 16 kHz 16-bit mono linear PCM in WAV container.
* **Code Evidence**:
  * [`backend/app/config.py:17-21`](file:///e:/VoiceQueue(gnani.ai)/backend/app/config.py#L17-L21):
    ```python
    TTS_MODEL = "timbre-v2.5"
    VALID_VOICES = {
        "te-IN": ["Lavanya"],
        "en-IN": ["Trupti"],
    }
    ```
  * [`backend/app/services/gnani.py:353-373`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L353-L373):
    ```python
    payload = {
        "text": processed_text,
        "voice": selected_voice,  # "Lavanya" or "Trupti"
        "model": "timbre-v2.5",
        "language": tts_lang,     # "te-IN" or "en-IN"
        ...
    }
    client.post(f"{BASE_URL}/api/v1/tts/inference", headers=headers, json=payload)
    ```

---

## 2. Real Voice Trial Results (Tests Page & Database Telemetry)

Data queried directly from the `voice_tests` table in [`voicequeue.db`](file:///e:/VoiceQueue(gnani.ai)/voicequeue.db) and [`frontend/src/VoiceTests.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/VoiceTests.jsx):

* **Total Formal Trials in Database (`voice_tests`)**: **0**
* **Language × Noise Condition Grid Breakdown**:
  * **Telugu (`te`)**:
    * Quiet Room: **NOT MEASURED** (0 of 0 trials)
    * Fan / AC Noise: **NOT MEASURED** (0 of 0 trials)
    * Street Noise: **NOT MEASURED** (0 of 0 trials)
    * Telugu Total: **NOT MEASURED** (0 of 0 trials)
  * **English (`en`)**:
    * Quiet Room: **NOT MEASURED** (0 of 0 trials)
    * Fan / AC Noise: **NOT MEASURED** (0 of 0 trials)
    * Street Noise: **NOT MEASURED** (0 of 0 trials)
    * English Total: **NOT MEASURED** (0 of 0 trials)
  * **Mix (`mix`)**:
    * Quiet Room: **NOT MEASURED** (0 of 0 trials)
    * Fan / AC Noise: **NOT MEASURED** (0 of 0 trials)
    * Street Noise: **NOT MEASURED** (0 of 0 trials)
    * Mix Total: **NOT MEASURED** (0 of 0 trials)
* **Overall Voice Trial Grid Total**: **NOT MEASURED** (0 of 0 trials logged)
* **Live System Audit Log (`voice_logs`)**: 128 general live interaction turns were captured during manual testing (`61 te-IN, 62 en-IN, 5 mix/te`), but all have `noise_label = null` because standard clinic turns do not ask users to label background acoustic conditions.

---

## 3. Text-Only Rule Test Results ("No Audio")

* **Primary Test Suite (`docs/test_phrases.csv`)**:
  * Label: **Text-only intent test (no audio)**
  * Verified dynamically by: [`backend/app/routers/voice_test_router.py:get_text_tests_summary()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/routers/voice_test_router.py#L96-L118)
  * Telugu (`te`): **15 of 15 passed** (100.0%)
  * English (`en`): **15 of 15 passed** (100.0%)
  * Mix (`mix`): **15 of 15 passed** (100.0%)
  * **Overall**: **45 of 45 passed (100.0%, no audio)**
* **Extended Benchmark Suite (`backend/tests/test_rule_accuracy.py`)**:
  * Label: **Rule accuracy benchmark across long sentences, misspellings, and negations (no audio)**
  * Overall: **60 of 60 passed (100.0%, no audio)**

---

## 4. Real Limitations Visible in the Code

1. **Intents Supported**: Exactly 6 discrete intents are handled in [`backend/app/services/intent.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py): `BOOK`, `STATUS`, `CANCEL`, `YES`, `NO`, and `UNKNOWN`. Medical triage, general medical questions, and doctor selection are not supported.
2. **Deterministic Rule-Based Intent**: Gnani provides speech perception (STT/TTS) but no conversational LLM chat model. All intent decisions and date calculations use regex and keyword matching.
3. **Language Scope**: Only Telugu (`te`), English (`en`), and Mix (`mix`) are supported. Other Indian languages (Hindi, Tamil, Kannada) are not implemented.
4. **Credit & Demo Limits**: Strict in-memory and database safeguards enforce:
   * 6 voice turns per 10 minutes per IP
   * 30 voice turns per day per IP
   * 10 voice turns per session
   * 150 real calls per day globally (`GNANI_DAILY_CAP`)
   * 40 calls reserved for owner (`GNANI_RESERVE`)
5. **Synthetic Data Only**: All patient records and tokens are simulated; zero protected health information (PHI) or phone numbers are stored.
6. **Logged Failures**: In `voice_logs`, 17 of 128 recorded turns failed (`ok=False`) due to intentionally tested validation gates: audio shorter than 0.5s, silence (RMS < 0.005), or rate-limit thresholds.

---

## 5. End-to-End Verified Working Features

1. **`book`**: Works end-to-end. Voice or text turn books next available token for today or tomorrow, writes to SQLite, broadcasts WebSocket event, and replies with spoken confirmation.
2. **`status`**: Works end-to-end. Looks up active patient token, computes exact waiting count ahead, and replies with spoken status.
3. **`cancel` & `confirmation`**: Works end-to-end. Requesting cancellation puts session in `confirm-cancel` state; answering "yes" cancels the token and frees the queue position.
4. **`live dashboard`**: Works end-to-end. Real-time receptionist dashboard connects to `/ws/queue`, updating summary KPIs, waiting list, active consultation, and voice activity feed instantly.
5. **`English/Telugu voice reply`**: Works end-to-end. Dynamic replies synthesize speech via Gnani Timbre `timbre-v2.5` (`Lavanya` / `Trupti`). Numbers are spelled out phonetically as words.
6. **`caching`**: Works end-to-end. Fixed prompts (greetings, confirmations, say-again) load from disk in `backend/cache/audio/`, returning audio instantly with zero Gnani calls and zero credit cost.

---

## 6. Fact-Check of Specific Claims

| Claim Statement | Verdict | Code / File Evidence |
| :--- | :---: | :--- |
| "Patient speaks Telugu or English to book, check and cancel" | **VERIFIED** | Implemented in [`backend/app/routers/turn_router.py:voice_turn()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/routers/turn_router.py#L42-L135) and [`frontend/src/App.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.jsx). |
| "Clinic dashboard updates live" | **VERIFIED** | Real-time WebSocket connection to `/ws/queue` in [`backend/app/main.py:75`](file:///e:/VoiceQueue(gnani.ai)/backend/app/main.py#L75) updates [`frontend/src/ClinicDashboard.jsx:120-165`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/ClinicDashboard.jsx#L120-L165). |
| "Built solo" | **VERIFIED** | Git repository history confirms 100% commits authored solo by D. Steven Son; credited in [`frontend/src/AboutPage.jsx:256`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.jsx#L256). |
| "Uses Gnani Prisma for speech to text" | **VERIFIED** | Code calls `POST https://api.vachana.ai/stt/v3` with `"model": "prisma-v3.0"` in [`backend/app/services/gnani.py:268-285`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L268-L285). |
| "Uses Gnani Timbre for voice replies" | **VERIFIED** | Code calls `POST https://api.vachana.ai/api/v1/tts/inference` with `"model": "timbre-v2.5"` in [`backend/app/services/gnani.py:355-373`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L355-L373). |
| "Synthetic data only" | **VERIFIED** | Database has no PII fields; [`backend/app/services/privacy.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/privacy.py) redacts phone/Aadhaar numbers; [`AboutPage.jsx:118`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.jsx#L118). |
| "Fixed phrases are cached to save credits" | **VERIFIED** | Pre-rendered audio loaded from [`backend/cache/audio/`](file:///e:/VoiceQueue(gnani.ai)/backend/cache/audio) via `get_cached_audio()` in [`backend/app/services/audio.py:310-330`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/audio.py#L310-L330). |
| "Intent is rule-based, not Gnani" | **VERIFIED** | Intent parsing is implemented with regex and keywords in [`backend/app/services/intent.py:250-400`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py#L250-L400) because Gnani provides no LLM. |
| "Handles mixed Telugu and English" | **VERIFIED** | Gnani STT configured with `"format": "codemix"`, `"language_code": "te-IN,en-IN"` ([`gnani.py:269-270`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L269-L270)) and code-mix regex in [`intent.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py). |

---

## 7. Exact Summary Lines for LinkedIn Post

**[results]**:
> The rule-based intent engine achieved 45 of 45 passed (100.0%, no audio) across Telugu, English, and Mix phrases in the benchmark test suite, while formal 3x3 background noise voice trials stand at 0 of 0 (NOT MEASURED) in database telemetry.

**[limitation]**:
> The system is strictly scoped to 6 scheduling intents using deterministic rules without conversational LLM diagnosis, enforced by a 150-call daily cap and 10-turn session limit on synthetic clinic data.

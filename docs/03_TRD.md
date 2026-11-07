# Technical Requirements Document (TRD) — VoiceQueue

## 1. Architecture Overview

```
+---------------------------------------------------------------------------------+
|                                PATIENT BROWSER                                  |
|  - MediaRecorder / Web Audio PCM capture (16kHz mono)                           |
|  - React 18 SPA (Patient View, Dashboard, Voice Tests, About, Audio Lab)       |
|  - HTMLAudioElement (One shared player, blob URL auto-cleanup, 0.85x slow audio)|
|  - WebSocket listener for live queue_changed & voice_log events                |
+---------------------------------------+-----------------------------------------+
                                        | HTTP POST /voice/turn (multipart audio)
                                        | HTTP POST /text/turn (JSON)
                                        | WS /ws (Live updates)
                                        v
+---------------------------------------------------------------------------------+
|                               FASTAPI BACKEND                                   |
|                                                                                 |
|  [Security & Rate Limit Guards]                                                 |
|    - 10MB Audio Size & Extension Guard                                          |
|    - CreditProtection (Per-IP 10m/daily, Session Cap, Owner Reserve)            |
|                                                                                 |
|  [Audio Quality Pipeline]                                                       |
|    - WAV Header Repair & Validation                                             |
|    - FFmpeg PCM-16kHz mono conversion & Cleaning                                |
|    - Gates: Min 0.3s, Silence/RMS Check, Max 30s                                |
|                                                                                 |
|  [Turn Orchestration Engine]                                                    |
|    - Gnani Prisma v3.0 STT Client (One-at-a-time Lock + 1s Retry Guard)         |
|    - Privacy Masking (Phone & Name Redaction)                                   |
|    - Intent Parser (Hardened Keyword Scoring + RapidFuzz + Optional Groq)       |
|    - Queue Service (Day-partitioned tokens, SQLite/SQLAlchemy)                  |
|    - Reply Engine (Phonetic number conversion, Caching check)                   |
|    - Gnani Timbre v2.5 TTS Client (Lavanya te-IN, Trupti en-IN)                 |
|                                                                                 |
|  [Monitoring & Real-Time Broadcast]                                             |
|    - Structured JSON Request Logging                                            |
|    - WebSocket Connection Manager                                               |
+-------------------+-----------------------------------+-------------------------+
                    |                                   |
                    v                                   v
+-----------------------------------+   +-----------------------------------------+
|           LOCAL STORAGE           |   |            EXTERNAL SERVICES            |
|  - SQLite (voicequeue.db)         |   |  - Gnani API (api.vachana.ai)           |
|  - Audio Cache (18 standard WAVs) |   |      * STT: /stt/v3 (prisma-v3.0)       |
|                                   |   |      * TTS: /api/v1/tts/inference       |
|                                   |   |             (timbre-v2.5)               |
|                                   |   |  - Groq API (Optional fallback NLU)     |
+-----------------------------------+   +-----------------------------------------+
```

---

## 2. Tech Stack & Dependency Versions

### Backend (`backend/requirements.txt`)
- **Python**: 3.11+
- **fastapi**: `>=0.111.0` (REST routing, dependency injection, OpenAPI documentation)
- **uvicorn[standard]**: `>=0.30.1` (ASGI web server)
- **python-multipart**: `>=0.0.9` (Multipart form-data parsing for audio uploads)
- **sqlalchemy**: `>=2.0.31` (SQL ORM and connection pooling)
- **python-dotenv**: `>=1.0.0` (Environment variable loading)
- **pydantic**: `>=2.0.0` (Request/response data validation and schemas)
- **websockets**: `>=12.0` (Real-time duplex event streaming)
- **httpx**: `>=0.27.0` (Async/sync HTTP client with connection pooling)
- **rapidfuzz**: `>=3.0.0` (Fuzzy string matching for phonetic and typo tolerance)
- **ffmpeg**: System binary for audio transcoding to PCM 16kHz mono

### Frontend (`frontend/package.json`)
- **react**: `^18.3.1` (User interface library)
- **react-dom**: `^18.3.1` (DOM renderer for React)
- **vite**: `^5.4.11` (Bundler, dev server, and asset optimizer)
- **vitest**: `^2.1.8` (Unit test framework)
- **jsdom**: `^30.1.3` (DOM simulation for unit tests)
- **@playwright/test**: `^1.64.1` (End-to-end browser automation)
- **@axe-core/playwright**: `^4.14.0` (Automated WCAG accessibility audit)
- **@testing-library/react**: `^16.3.3` (Component test utilities)

---

## 3. Backend Modules & Responsibilities

| Module | Location | Responsibilities |
| :--- | :--- | :--- |
| `config` | `backend/app/config.py` | Environment variable definitions, timbre voice validation, voice sanitization. |
| `db` | `backend/app/db.py` | SQLAlchemy database engine, session factory, schema table generation. |
| `models` | `backend/app/models.py` | ORM entities: `Token`, `VoiceLog`, `GnaniUsage`, `AudioCompare`, `ErrorCount`. |
| `schemas` | `backend/app/schemas.py` | Pydantic data schemas for request payloads, API serialization, and health response. |
| `main` | `backend/app/main.py` | FastAPI app creation, ASGI lifespan hooks, CORS middleware, structured logging middleware. |
| `queue_router` | `backend/app/routers/queue_router.py` | Queue endpoints: `/queue/tokens`, `/tokens/{id}`, `/tokens/call-next`, `/demo/reset`. |
| `turn_router` | `backend/app/routers/turn_router.py` | Interaction endpoints: `/voice/turn`, `/text/turn`, `/voice/retry-audio`, `/voice-logs`, `/usage`. |
| `voice_test_router` | `backend/app/routers/voice_test_router.py` | Evaluation routes: `/voice-tests/run`, `/voice-tests/run-csv`, `/voice-tests/text-summary`. |
| `audio` | `backend/app/services/audio.py` | WAV header validation, WAV repairs, FFmpeg conversion, audio cleaning, cache scan. |
| `broadcast` | `backend/app/services/broadcast.py` | WebSocket broadcast wrappers for queue changes, token called alerts, and voice feed. |
| `credit_protection` | `backend/app/services/credit_protection.py` | Rate-limiting (per-IP, session, daily cap, owner reserve), client IP extraction. |
| `error_catalog` | `backend/app/services/error_catalog.py` | Standardized error code mapping and bilingual patient error messages. |
| `gnani` | `backend/app/services/gnani.py` | Low-level HTTP communication with Gnani Prisma STT and Timbre TTS. |
| `intent` | `backend/app/services/intent.py` | Rule-based intent parser, slot extraction, fuzzy scoring, and Groq fallback. |
| `latency_tracker` | `backend/app/services/latency_tracker.py` | Millisecond stage latency recording (conversion, cleaning, STT, intent, queue, TTS). |
| `monitoring` | `backend/app/services/monitoring.py` | Structured JSON request logging, error counters, uptime measurement. |
| `number_words` | `backend/app/services/number_words.py` | Phonetic number-to-words converters for Telugu (`సున్నా`..`ఇరవై`) and English. |
| `privacy` | `backend/app/services/privacy.py` | Regex masking of Indian mobile numbers and personal names. |
| `queue_service` | `backend/app/services/queue_service.py` | Token booking logic, daily sequencing, waiting position calculations, auto-seeding. |
| `replies` | `backend/app/services/replies.py` | Response text templates for booking, status, cancellation confirmation, and day prompts. |
| `turn_service` | `backend/app/services/turn_service.py` | Turn orchestration coordinator linking STT, intent, queue actions, replies, and TTS. |

---

## 4. Frontend Structure

- **`frontend/src/main.jsx`**: Bootstraps the React DOM tree.
- **`frontend/src/App.jsx`**: Main patient application interface.
  - Manages mic recording lifecycle (`idle` -> `recording` -> `processing` -> `playing`).
  - Implements **one shared `HTMLAudioElement`** with automatic blob URL revocation between consecutive turns.
  - Controls view navigation: `/` (patient), `/clinic` (dashboard), `/tests` (tests), `/about` (about), `/audio-lab` (audio lab).
  - Listens to active WebSocket connections for live queue updates and alerts.
- **`frontend/src/ClinicDashboard.jsx`**: Receptionist and doctor dashboard for queue monitoring, calling next tokens, and demo reset.
- **`frontend/src/VoiceTests.jsx`**: Automated speech evaluation harness for executing benchmark phrases with quiet/fan/street noise labels.
- **`frontend/src/AboutPage.jsx`**: Transparent documentation page showing named Gnani models, dynamic text intent metrics, and limitations.
- **`frontend/src/AudioLab.jsx`**: Developer audio comparison interface for comparing raw vs. cleaned voice clips.
- **`frontend/src/audioCapture.js`**: Cross-browser audio recording utilities supporting 16kHz mono WAV export.
- **`frontend/src/timeUtils.js`**: Shared IST formatting helper enforcing `Asia/Kolkata` across feed and header views.

---

## 5. Gnani Integration Details

- **Base URL**: `https://api.vachana.ai` (`backend/app/services/gnani.py#L16`).
- **One-Request-at-a-Time Rule**:
  - Enforced via a global threading lock (`_gnani_lock = threading.Lock()`).
  - Wrapped with an automatic 1-second retry guard (`_execute_with_lock_and_retry`) for network errors, 5xx responses, or 429 rate limits.
- **STT (Speech-to-Text)**:
  - **Endpoint**: `POST https://api.vachana.ai/stt/v3`
  - **Model**: `prisma-v3.0`
  - **Format**: `codemix` (supports mixed vernacular Telugu and English)
  - **Language Code**: `te-IN,en-IN` (for Telugu and Mix modes) or `en-IN` (for English mode)
  - **Request Fields**: `audio_file` (WAV bytes), `model`, `language_code`, `format`, `keyterms`, `topic`
  - **Keyterms**: Custom clinic vocabulary (`token`, `appointment`, `clinic`, `cancel`, `status`, `today`, `tomorrow`, `repu`, `ivala`, `kavali`, `raddu`)
- **TTS (Text-to-Speech)**:
  - **Endpoint**: `POST https://api.vachana.ai/api/v1/tts/inference`
  - **Model**: `timbre-v2.5`
  - **Voices per Language**:
    - Telugu (`te-IN`): `Lavanya` (female)
    - English (`en-IN`): `Trupti` (female)
  - **Request Payload**:
    - `text`: Spoken text (with all numeric digits pre-converted to phonetic words)
    - `voice`: `Lavanya` or `Trupti`
    - `model`: `timbre-v2.5`
    - `language`: `te-IN` or `en-IN`
    - `speed`: `1.0`
    - `audio_config`: `{"sample_rate": 16000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}`
- **Error Codes Handled**:
  - `400`: Wrong model, language mismatch, or unsupported voice -> raises `VoiceNotSupportedError`
  - `401`: Bad or missing API key -> raises `GnaniAuthError`
  - `402`: Out of credits -> raises `GnaniNoCreditsError`
  - `403`: Forbidden / permission denied -> raises `GnaniForbiddenError`
  - `429`: Rate limit exceeded -> raises `GnaniRateLimitError`
  - `5xx` / Network Timeout: Retries once after 1s; if failing, raises `GnaniAPIError`

---

## 6. Intent Parsing Logic

Implemented in `backend/app/services/intent.py`:
1. **Normalization & Filtering**:
   - Removes greetings and polite words (e.g., `hello`, `please`, `namaskaram`, `dayachesi`, `andi`, `daktar garu`).
   - Masks and redacts personal names and phone numbers before keyword matching.
2. **Keyword Scoring with Fuzzy Matching**:
   - Compares normalized text against keyword sets for `BOOK`, `STATUS`, `CANCEL`, `YES`, and `NO`.
   - Uses `rapidfuzz.fuzz.token_set_ratio` with an 85.0 confidence threshold to handle typos and spelling variants.
3. **Precedence & Negation**:
   - Negations (`don't cancel`, `cancel vaddu`, `cheyyoddu`, `kaadu`) explicitly block cancellation and route to `NO`.
   - Conflicting actions (both book and cancel words present) trigger `CLARIFY`.
   - Priority tie-breaking: `CANCEL` > `STATUS` > `BOOK` > `YES` > `NO`.
4. **Day Slot Extraction**:
   - Identifies "today" (`today`, `ee roju`, `ivala`, `ఈ రోజు`, `ఈరోజు`) and "tomorrow" (`tomorrow`, `repu`, `రేపు`, `రేపటికి`).
   - The word `kal` is explicitly ignored due to regional ambiguity.
   - If no day word is found during booking, returns `day=None` so the system prompts "Today or tomorrow?".
5. **Optional Groq Fallback**:
   - If keyword confidence is below `0.4` and `GROQ_API_KEY` is configured, calls `llama-3.1-8b-instant` with temperature `0.0` and JSON schema output.

---

## 7. Audio Pipeline

1. **Client Recording**:
   - Captures microphone input via Web Audio API or `MediaRecorder`.
   - Encodes as PCM 16kHz mono WAV or WebM/MP4.
2. **Upload & Header Repair**:
   - Uploaded to `/voice/turn` with max size limit of 10 MB.
   - `repair_wav_header()` fixes `RIFF` chunk sizes if corrupted or zeroed during mobile recording.
3. **Transcoding (FFmpeg)**:
   - `convert_to_pcm16_wav()` uses FFmpeg to enforce 16kHz sample rate, 16-bit depth, mono audio.
4. **Quality Gates**:
   - Duration check: Rejects files < 0.3s (`too_short`) or > 30s (`too_long`).
   - RMS Energy check: Rejects audio with RMS < 0.005 (`too_quiet` / silence).
   - Clipping check: Detects clipped peaks (> 0.99 amplitude).
5. **Caching of Fixed Phrases**:
   - Standard responses (`ask_day_te`, `ask_day_en`, `cancelled_te`, `cancelled_en`, `say_again_te`, `say_again_en`, etc.) are pre-synthesized and stored in `backend/cache/audio/`.
   - Standard responses bypass live TTS calls, executing with zero latency and zero credit consumption.

---

## 8. Queue Management Logic

Implemented in `backend/app/services/queue_service.py`:
- **Token Sequencing**:
  - Tokens are partitioned by calendar date (`YYYY-MM-DD`).
  - Token numbers increment sequentially starting from 1 for each date.
- **Position Tracking**:
  - `position(db, token_id)` calculates the number of active `waiting` tokens with smaller sequence numbers for the same date.
- **Status Transitions**:
  - `waiting` -> `called` -> `done` (or `cancelled` / `no_show`).
- **Auto-Seeding**:
  - If the database queue is empty on startup and `DEMO_AUTOSEED=true`, seeds 4 initial demo tokens (`Demo Patient 1–4`).
- **Concurrency Protection**:
  - Synchronized SQLite transactions prevent duplicate token number assignment during concurrent bookings.

---

## 9. WebSocket Events

Managed by `backend/app/services/connection_manager.py` over `/ws`:
- **`queue_changed`**: Broadcast when a token is booked, cancelled, or status changes. Payload: `{"type": "queue_changed", "date": "YYYY-MM-DD"}`.
- **`token_called`**: Broadcast when clinic staff calls a patient. Payload includes token number, patient label, and sound alert trigger.
- **`demo_reset`**: Broadcast when clinic staff resets the queue, notifying connected clients to clear active polling.
- **`voice_log`**: Broadcast immediately after every completed voice turn to update the live activity feed on all connected screens.

---

## 10. Demo & Credit Rate Limits

Guarded by `backend/app/services/credit_protection.py`:
- **`DEMO_LIMITS`**:
  - When `DEMO_LIMITS=off`: Rate limits and reserves are bypassed for local testing.
  - When `DEMO_LIMITS=on`: Strict production limits are enforced.
- **Per-IP Limits**:
  - 6 voice turns per 10 minutes (`RATE_LIMIT_VOICE_10MIN = 6`).
  - 30 voice turns per day (`RATE_LIMIT_VOICE_DAILY = 30`).
- **Per-Session Cap**:
  - 10 voice turns per unique browser session (`SESSION_VOICE_CAP = 10`).
- **Global Daily Cap**:
  - Capped by `GNANI_MAX_CALLS` (default 150 calls/day).
- **Owner Reserve**:
  - `GNANI_RESERVE = 40` calls reserved exclusively for the owner.
  - Non-owner requests are blocked with a friendly demo limit message when fewer than 40 calls remain.
- **Owner Bypass**:
  - Adding header `X-Owner-Key: <OWNER_KEY>` bypasses IP rate limits, session caps, and reserve blocks.

---

## 11. Environment Variables

| Variable Name | Purpose |
| :--- | :--- |
| `GNANI_API_KEY` | API secret key for Gnani Prisma STT and Timbre TTS. |
| `GNANI_MAX_CALLS` | Hard maximum ceiling on real Gnani API calls per day. |
| `GNANI_DAILY_CAP` | Configured daily credit limit for the clinic deployment. |
| `GNANI_RESERVE` | Number of calls reserved exclusively for owner demonstrations. |
| `OWNER_KEY` | Secret token enabling owner bypass of public rate limits. |
| `VOICE_TE` | Name of the configured Telugu TTS voice model (`Lavanya`). |
| `VOICE_EN` | Name of the configured English TTS voice model (`Trupti`). |
| `DATABASE_URL` | SQLAlchemy connection string (default SQLite: `sqlite:///./voicequeue.db`). |
| `CORS_ORIGINS` | Allowed origins for web browser Cross-Origin Resource Sharing. |
| `CLINIC_NAME` | Clinic title displayed in application headers and cards. |
| `GROQ_API_KEY` | Optional key for Groq Llama-3.1 fallback intent classification. |
| `DEMO_LIMITS` | Flag (`on` / `off`) enabling or disabling public rate limiting. |
| `DEMO_AUTOSEED` | Flag (`true` / `false`) controlling automatic demo queue seeding on startup. |
| `DEBUG_SAVE_AUDIO` | Flag (`true` / `false`) controlling diagnostic disk caching of incoming audio. |

---

## 12. Security Measures

1. **PII Masking**: Indian mobile phone numbers (10 digits starting with 6–9) and patient names are stripped via regex before transcripts are stored or forwarded.
2. **Secret Masking**: `sanitize_gnani_error()` scrubs API keys, bearer tokens, and secrets from all server logs and error messages.
3. **Payload Size Restrictions**: File uploads to `/voice/turn` are strictly capped at 10 MB with media extension validation.
4. **Endpoint Rate Limiting**: Sensitive admin endpoints (`/demo/reset`, `/demo/seed`) are rate-limited and owner-key protected on deployed builds.
5. **Offline Test Firewall**: Test harnesses (`backend/tests/conftest.py`) utilize strict socket monkeypatching that blocks outbound network traffic.

---

## 13. Error Handling

- Centralized error taxonomy defined in `shared/error_catalog.json` and mirrored in `backend/app/services/error_catalog.py` and `frontend/src/errorCatalog.js`.
- Errors return standard JSON responses with machine-readable error codes (`demo_limit`, `audio_too_short`, `too_quiet`, `tts_invalid_audio`, etc.) and localized patient-friendly messages.
- The application never leaks internal Python tracebacks or database details to the client UI.

---

## 14. Known Limitations

1. **Rule-Based Intent Routing**: Intent parsing is rule-driven rather than an LLM agent; novel colloquial phrasing outside keywords relies on fuzzy matching or optional Groq fallback.
2. **Batch STT Processing**: Audio is processed as a completed audio clip rather than real-time streaming STT.
3. **Single Clinic Scope**: Architecture supports a single clinic queue per database instance.
4. **Synthetic Data**: Queue records represent synthetic demonstration data only.

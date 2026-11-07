# VoiceQueue Setup, Configuration & Maintenance Guide

**Document**: `08_SETUP_AND_MAINTENANCE.md`  
**Application**: VoiceQueue (`gnani.ai`)  
**Target Environment**: Local Developer Workstation & Staging/Production Deployments  

---

## 1. Prerequisites & System Dependencies

Ensure the following runtimes and system binaries are installed and available on your system `PATH`:

1. **Python 3.11+**:
   * Verify: `python --version`
   * Used for FastAPI backend, SQLite database interactions, and audio processing services.
2. **Node.js 18+ or 20+ (with npm)**:
   * Verify: `node -v` and `npm -v`
   * Used for the React frontend, Vite development server, and Playwright tests.
3. **FFmpeg**:
   * Verify: `ffmpeg -version`
   * **Required** for incoming audio conversion from browser formats (`audio/webm`, `audio/mp4`, `audio/ogg`) to 16 kHz 16-bit mono PCM WAV for Gnani Prisma STT.
   * *Windows*: Install via `winget install Gyan.FFmpeg` or `choco install ffmpeg`.
   * *macOS*: Install via `brew install ffmpeg`.
   * *Linux (Ubuntu/Debian)*: `sudo apt update && sudo apt install -y ffmpeg`.

---

## 2. Environment Variables Specification

VoiceQueue reads configuration from environment variables defined in `.env` (or `backend/.env`).

> [!CAUTION]
> **Security Notice**: Never commit `.env` or paste actual API keys into documentation, tickets, or pull requests. Below are the variable **names** and their technical purposes only.

| Environment Variable Name | Purpose & Behavior | Default (if omitted) |
| :--- | :--- | :--- |
| `ENV` | Environment identifier (`development`, `staging`, `production`). Controls debug flags and limit defaults. | `development` |
| `DEMO_LIMITS` | Rate limiting toggle (`on` or `off`). When `off`, disables per-IP, per-session, and reserve throttling. | Auto (`off` in dev/localhost, `on` in prod) |
| `GNANI_API_KEY` | Authentication bearer token used in request headers for Gnani Prisma STT and Timbre TTS. | Empty string |
| `GNANI_DAILY_CAP` | Global daily hard limit of real Gnani API calls across all users before voice is paused. | `150` |
| `GNANI_MAX_CALLS` | Fallback alias for daily call quota. | `300` |
| `GNANI_RESERVE` | Number of daily calls reserved exclusively for requests carrying `X-Owner-Key`. | `40` |
| `RATE_LIMIT_VOICE_10MIN` | Maximum number of voice turns permitted per IP address in any sliding 10-minute window. | `6` |
| `RATE_LIMIT_VOICE_DAILY` | Maximum number of voice turns permitted per IP address in a 24-hour day. | `30` |
| `SESSION_VOICE_CAP` | Maximum number of voice turns permitted per unique browser session identifier. | `10` |
| `OWNER_KEY` | Secret access token allowing administrator/evaluator bypass of IP rate limits and reserve lock. | Empty string |
| `DEMO_VIDEO_URL` | Optional YouTube or Loom demo video URL returned to users when daily limits are exhausted. | Empty string |
| `GNANI_CREDITS_PER_CALL` | Optional multiplier used to compute estimated credit consumption in the dashboard. | Empty string |
| `VOICE_TE` | Speaker voice name for Telugu TTS synthesis via Gnani Timbre `timbre-v2.5` (must be `Lavanya`). | `Lavanya` |
| `VOICE_EN` | Speaker voice name for English TTS synthesis via Gnani Timbre `timbre-v2.5` (must be `Trupti`). | `Trupti` |
| `DATABASE_URL` | SQLAlchemy database connection string (e.g., `sqlite:///./voicequeue.db`). | `sqlite:///./voicequeue.db` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins for cross-origin browser requests. | `http://localhost:5173,http://127.0.0.1:5173` |
| `CLINIC_NAME` | Display name of the medical clinic displayed across the header and responses. | `Demo Clinic` |
| `GROQ_API_KEY` | Optional API key for Groq NLU fallback (Llama-3.1-8B-Instant) when rule parsing fails. | Empty string |
| `AUDIO_CLEAN` | Boolean flag enabling bandpass (150Hz–3800Hz) and mild acoustic gate filtering on user audio. | `true` |
| `DEBUG_SAVE_AUDIO` | When `true`, saves raw and cleaned user audio recordings to `backend/cache/debug_audio/`. | `false` |
| `DEV_ENDPOINTS` | Enables `/dev/limits`, `/dev/latency`, and `/dev/error-counts` diagnostic endpoints. | `false` |
| `COMPARE_MAX_CALLS` | Quota of uncleaned raw audio calls allowed in Audio Compare evaluation mode. | `20` |

---

## 3. Step-by-Step Local Setup & Execution

### 3.1 Backend Setup
1. Open a terminal in the project root:
   ```bash
   cd e:\VoiceQueue(gnani.ai)
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```
   *(Edit `.env` to supply `GNANI_API_KEY`)*.

5. Start the backend server:
   ```bash
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   * Backend will be live at: `http://127.0.0.1:8000`
   * Interactive OpenAPI documentation: `http://127.0.0.1:8000/docs`
   * Health endpoint: `http://127.0.0.1:8000/health`

### 3.2 Frontend Setup
1. In a separate terminal, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node.js packages:
   ```bash
   npm install
   ```
3. Launch Vite development server:
   ```bash
   npm run dev
   ```
   * Patient Voice App: `http://localhost:5173/`
   * Clinic Reception Dashboard: `http://localhost:5173/clinic`
   * Voice Testing Telemetry: `http://localhost:5173/tests`
   * About & Models Overview: `http://localhost:5173/about`

### 3.3 Running Test Suites
* **Backend Pytest Suite**:
  ```bash
  pytest backend/tests/ -v
  ```
* **Frontend Unit & Component Tests**:
  ```bash
  cd frontend
  npm test
  ```
* **Frontend Playwright End-to-End Tests**:
  ```bash
  cd frontend
  npx playwright test
  ```

---

## 4. How `DEMO_LIMITS` and Credit Protection Work

VoiceQueue includes a multi-layered guard system defined in [`backend/app/services/credit_protection.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/credit_protection.py) to prevent accidental credit exhaustion on publicly deployed sites:

### 4.1 Throttling Layers
1. **Per-IP Sliding Window**: Limits each unique remote IP to **6 voice turns per 10 minutes** and **30 turns per day**.
2. **Per-Session Cap**: Limits a single browser session to **10 voice turns**.
3. **Daily Quota Cap (`GNANI_DAILY_CAP=150`)**: When total real calls today reach 150, live voice interactions pause globally.
4. **Owner Reserve Buffer (`GNANI_RESERVE=40`)**: When remaining daily calls hit 40, public visitors are paused; only the owner can trigger voice turns.
5. **Fallback to Typing**: When limits are reached, the application **never crashes**. It automatically switches to typed fallback (`/text/turn`) which continues booking and managing tokens while serving spoken replies strictly from pre-rendered cache files.

### 4.2 Toggling `DEMO_LIMITS`
* **Local Development**: By default, `DEMO_LIMITS` is automatically **inactive** when running on `127.0.0.1` or `localhost`, allowing developers to test freely without rate limits.
* **Forcing Limits On Locally**: Set `DEMO_LIMITS=on` in `.env` to test the rate-limiting banners and fallback behavior.
* **Forcing Limits Off in Staging**: Set `DEMO_LIMITS=off` in `.env` to disable all throttling.

### 4.3 Administrator / Evaluator Bypass
To test a deployment where limits are active without hitting rate barriers:
1. Append `?owner=1` to the URL: `http://localhost:5173/?owner=1`.
2. Enter the secret key matching `OWNER_KEY` in the top bar.
3. The client stores the key in `sessionStorage` and includes the header `X-Owner-Key: <key>` on all API requests, bypassing IP and session caps.

---

## 5. Credit Counting & Usage Tracking

Credit usage is tracked in the database table `gnani_usage` ([`backend/app/models.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/models.py#L7-L21)):
* Every real HTTP call to Gnani Prisma STT logs: `kind='stt'`, `cached=False`.
* Every real HTTP call to Gnani Timbre TTS logs: `kind='tts'`, `cached=False`.
* Fixed phrase responses (greetings, confirmations, say-again prompts) served from disk log: `cached=True`.
* Inspection:
  * Reception dashboard displays live usage badge (`Gnani calls: X/150`).
  * REST endpoint: `GET /usage` returns real vs cached call counts.

---

## 6. Audio Cache Management & In-Place WAV Repair

To minimize API consumption, VoiceQueue caches pre-rendered audio for all standard responses in [`backend/cache/audio/`](file:///e:/VoiceQueue(gnani.ai)/backend/cache/audio).

### 6.1 Audio Cache Scan and Repair
On every application startup, [`scan_and_clean_audio_cache()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/audio.py#L646-L680) runs automatically:
1. **WAV Header Correction**: Fixes corrupted or zero-length RIFF headers in-place by computing real file byte sizes.
2. **Quality Gate Re-validation**: Verifies every cached WAV file has valid PCM formatting and duration >= 0.3s.
3. **Truncated File Purging**: Safely purges zero-byte or corrupted files.

### 6.2 Pre-Generating Fixed Phrase Cache
Run the cache build script to populate standard audio files without starting the server:
```bash
python scripts/build_cache.py
```
To verify the integrity of all cached WAV files without making any API calls:
```bash
python scripts/check_cache.py
```

---

## 7. Troubleshooting & Common Errors

| Error Code / Symptom | Root Cause | Resolution & Verification |
| :--- | :--- | :--- |
| **HTTP 401 Unauthorized** | `GNANI_API_KEY` is missing, expired, or invalid. | Verify `GNANI_API_KEY` in `.env`. Ensure no leading/trailing quotes or spaces. Check `/health`. |
| **HTTP 402 Payment Required** | Gnani account credits depleted. | Recharge credits in Gnani portal. The app will automatically fallback to serving cached voice and typing. |
| **HTTP 403 Forbidden** | Accessing developer endpoints (`/dev/limits`, `/dev/latency`) with `DEV_ENDPOINTS=false`. | Set `DEV_ENDPOINTS=true` in `.env` to enable developer telemetry. |
| **HTTP 429 Too Many Requests** | IP rate limit exceeded (6/10m) or demo reset limit triggered. | Wait for the 60s cooldown window, or provide `OWNER_KEY` via `?owner=1` to bypass throttling. |
| **HTTP 400 Bad Request (Wrong Voice)** | Voice parameter not supported by `timbre-v2.5`. | Set `VOICE_TE=Lavanya` and `VOICE_EN=Trupti` in `.env`. Restart backend. |
| **"Audio too short" or "Too quiet"** | Patient spoke under 0.5 seconds or microphone volume was near zero (RMS < 0.005). | Advise patient to speak louder or move mic closer. Use the `🎙️ Mic check` tool to calibrate. |
| **Browser Audio Not Playing (Autoplay blocked)** | Modern mobile browsers block audio playback until user interacts with the page. | Tap the `🔊 Tap to hear the reply` fallback button or dismiss the first-visit notice banner. |
| **FFmpeg Not Found** | FFmpeg binary is missing from system `PATH`. | Install FFmpeg and verify with `ffmpeg -version`. Restart the backend terminal session. |

---

## 8. Resetting Demo Data

To wipe patient records and reset the queue to a clean state for a presentation:

### Option A: From Reception Dashboard UI
1. Open `http://localhost:5173/clinic`.
2. Click the `🔄 Reset Demo` button in the top action bar.
3. To reload synthetic patient cards, click `🌱 Seed Demo Data (1-6)`.

### Option B: Via REST API
```bash
# Reset all tokens and voice logs
curl -X POST http://127.0.0.1:8000/demo/reset

# Seed 4 demo tokens for today
curl -X POST "http://127.0.0.1:8000/demo/seed?day=today&count=4"
```

### Option C: Via CLI Script (Even if server is offline)
```bash
python scripts/demo_reset.py --count 4
```
This directly re-initializes SQLite database tables and injects sequential demo patients without requiring any external network or Gnani calls.

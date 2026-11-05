# VoiceQueue

> **Voice-first clinic token and queue management system for Demo Clinic**  
> Supporting Telugu (తెలుగు), English, and Mix (Telugu + English) using Gnani AI REST speech models.

---

## 1. The Problem

In Indian outpatient (OPD) clinics, walk-in token queues are often chaotic, crowded, and stressful. Patients who cannot read or write, as well as elderly visitors, struggle with digital touchscreens, printed paper tokens, and complex smartphone apps. 

**VoiceQueue** solves this with a **voice-first, mobile-accessible assistant**. Patients simply hold a single microphone button and speak in their natural language (Telugu, English, or conversational Mix) to book a token, check how many patients are ahead in line, or cancel an appointment. Spoken replies are delivered back instantly with all numbers pronounced as natural words.

---

## 2. Core Features

- **Patient Mobile App (`/`)**:
  - High-contrast, mobile-first design with 56px+ touch targets and accessible Noto Sans fonts.
  - Large 110px hold-to-talk microphone button with a pulsing animation ring and 8-second auto-stop timer.
  - Instant audio replay without re-querying the API.
  - Real-time token status card polling position updates every 5 seconds.
  - 60-second cancel confirmation memory (*"Are you sure?"* -> Yes/No buttons).
  - Automatic fallback to typed input if microphone permission is denied or daily credits are exhausted.
- **Clinic Live Dashboard (`/clinic`)**:
  - Real-time operational overview for receptionists and doctors.
  - Auto-reconnecting WebSocket (`/ws/queue`) streaming instantaneous queue changes.
  - *Today* and *Tomorrow* tabbed views.
  - *Now in Consultation* card with single-click *Mark Done* and *No-Show* actions.
  - Ordered *Waiting* queue with glowing highlight animation on new tokens.
  - Live *Voice Activity* telemetry feed showing transcripts, intents, and timestamps.
  - Instant demo management: *Call Next Patient*, *Seed Demo Patients*, and *Reset Demo Queue*.
- **Credits Meter & Safety Guard**:
  - Real-time dashboard meter (`Gnani calls: 42/300`).
  - Color-coded safety thresholds: normal teal, amber at 80%, red at 100%.
  - Safety shut-off blocking external API calls when the daily limit is reached.
  - Warning banner on all screens: *"Voice is paused to save credits. Typing still works."*
- **Testing & Noise Telemetry Suite (`/tests`)**:
  - Built-in empirical trial logger to record voice recognition accuracy across background noise conditions (*Quiet*, *Fan/AC*, *Street/Traffic*).
  - Live summary matrix of pass rates grouped by language and noise level.
  - 1-click **Export CSV** for offline analysis.
  - Automated offline text benchmark suite running 45 standardized phrases with 100.0% accuracy.
- **Zero-Digit Phonetic Speech**:
  - Numbers (0–99) in synthesized audio responses are rendered strictly into phonetic words (e.g., Telugu *"పదకొండు"*, English *"eleven"*). Raw numeric digits are never sent to the voice synthesizer.
- **Pre-Cached Prompts**:
  - Common fixed audio phrases (greetings, confirmations, service paused, repeat prompts) are pre-generated to save latency and preserve API credits.

---

## 3. Architecture

```text
 +-------------------------------------------------------------------------------+
 |                             VoiceQueue Architecture                           |
 +-------------------------------------------------------------------------------+
 |                                                                               |
 |   PATIENT BROWSER (Mobile-First UI)              CLINIC DASHBOARD (Desktop)   |
 |   Route: /                                       Route: /clinic, /tests       |
 |   - Hold-to-Talk (MediaRecorder webm)            - Live WebSocket Queue       |
 |   - Audio Replay (Base64 audio/wav)              - Consultation & Queue Ops   |
 |   - Token Card & Cancel Confirmation             - Live Voice Activity Feed   |
 |   - Auto Typed Input Fallback                    - Credits Meter & Telemetry  |
 |            |                                                ^                 |
 |      HTTP POST /voice/turn, /text/turn                      | WebSocket       |
 |            |                                                | /ws/queue       |
 |            v                                                v                 |
 |   +-----------------------------------------------------------------------+   |
 |   |                         FASTAPI BACKEND                               |   |
 |   |                                                                       |   |
 |   |  +--------------------+     +------------------+   +---------------+  |   |
 |   |  | ffmpeg Audio Guard | --> |   Rule-based NLU |   | Queue Service |  |   |
 |   |  | (16kHz Mono WAV)   |     | (Intent/Day slot)|   | (Tokens DB)   |  |   |
 |   |  +--------------------+     +------------------+   +---------------+  |   |
 |   |            |                         |                    |           |   |
 |   |            v                         v                    v           |   |
 |   |  +-----------------------------------------------------------------+  |   |
 |   |  |                   Gnani Speech Service Layer                    |  |   |
 |   |  | - Concurrency Lock (1 request at a time)                        |  |   |
 |   |  | - Daily Credit Limit Meter (Amber @ 80%, Red @ 100%)            |  |   |
 |   |  | - Pre-Cached Prompt Audio Cache (Telugu & English)              |  |   |
 |   |  | - Spoken Words Converter (0-99 phonetic numbers, no raw digits) |  |   |
 |   |  +-----------------------------------------------------------------+  |   |
 |   |            |                                              |           |   |
 |   +------------|----------------------------------------------|-----------+   |
 |                |                                              |               |
 |                v                                              v               |
 |      +--------------------+                         +-------------------+     |
 |      |  Prisma v3.0 (STT) |                         | Timbre v2.5 (TTS) |     |
 |      | (te-IN / en-IN)    |                         | (VOICE_TE/VOICE_EN|     |
 |      +--------------------+                         +-------------------+     |
 |                ^                                              ^               |
 |                +------------- Gnani AI Cloud -----------------+               |
 |                                                                               |
 +-------------------------------------------------------------------------------+
```

---

## 4. Setup & Running

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & npm
- **ffmpeg** installed and accessible in system `PATH` (used by `backend/app/services/audio.py` for conversion to 16kHz mono WAV)

### Step 1: Clone and Configure Environment
Configure your local environment variables:
```bash
git clone <repo-url>
cd VoiceQueue
cp .env.example .env
```

### Step 2: Backend Setup
Install Python dependencies:
```bash
pip install -r backend/requirements.txt
```

Pre-generate fixed audio prompts in `backend/cache/audio/`:
```bash
python scripts/build_cache.py
```

Run the backend server:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- Health Check: `http://127.0.0.1:8000/health`
- Credits Usage API: `http://127.0.0.1:8000/usage`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

### Step 3: Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Open in browser:
- **Patient Voice App**: `http://localhost:5173/`
- **Clinic Dashboard**: `http://localhost:5173/clinic`
- **Voice Tests Telemetry**: `http://localhost:5173/tests`
- **Audio Lab (Dev Tools)**: `http://localhost:5173/audio-lab?dev=1`
- **About & Limitations**: `http://localhost:5173/about`

---

## 5. Demo Recording Guide (/demo-mode)

To record a clean, professional demonstration video of the full voice and live queue flow:

### Exact Recording Steps
1. **Start the Servers**:
   - Backend: `uvicorn backend.app.main:app --reload --port 8000`
   - Frontend: `cd frontend && npm run dev`
2. **Open the Screens in Clean Mode** (`?clean=1` hides developer debug pills):
   - **Laptop / Tablet**: Open `http://localhost:5173/clinic?clean=1`
   - **Phone**: Open `http://<your-local-ip>:5173/?clean=1` (or split-screen browser at 390px mobile viewport)
3. **Reset and Seed Demo Data**:
   - On the Clinic Dashboard, press **`Shift+R`** on your keyboard (hidden shortcut) or click **Seed demo**.
   - This resets the queue and creates **4 fake tokens** (Token #1 in consultation, Tokens #2–4 waiting).
4. **Demonstrate Live Voice Flow**:
   - Hold the mic on the phone and speak: *"నాకు రేపు టోకెన్ కావాలి"* (or *"I need an appointment tomorrow"*).
   - Listen to the spoken reply and watch Token #5 appear live on the dashboard within 1 second via WebSocket without page refresh.
5. **Demonstrate Live Status Check**:
   - Hold the mic and ask: *"What is my token status?"* (or *"naa token number status"*).
   - The patient card updates with exact queue position (*"Ahead in queue: 3 patients"*).
6. **Demonstrate Consultation Progression**:
   - On the laptop dashboard, click **Call next** (Token #2 moves into consultation) and click **Mark done**.
   - Notice the ahead-counter on the phone update in real time.
7. **Demonstrate Cancellation**:
   - On the phone, say *"Cancel token"* -> tap the **Yes** confirmation button. The token is marked cancelled.

> **Zero Credit Waste via Pre-Cached Audio**: All fixed prompts (greetings, confirmations, cancellations, repetitions) are served directly from `backend/cache/audio/`, so the demo consumes minimal Gnani API calls.


---

## 5. Environment Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GNANI_API_KEY` | String | `""` | Gnani API access key for Prisma STT and Timbre TTS. |
| `GNANI_MAX_CALLS` | Integer | `300` | Daily safety limit for real Gnani API calls. Further calls are blocked. |
| `GNANI_CREDITS_PER_CALL` | Float | `None` | Optional multiplier to estimate total credit consumption in `/usage`. |
| `VOICE_TE` | String | `"Lavanya"` | Voice identifier for Telugu Timbre TTS. |
| `VOICE_EN` | String | `"Trupti"` | Voice identifier for English Timbre TTS. |
| `DATABASE_URL` | String | `sqlite:///./voicequeue.db` | SQLAlchemy database connection string. |
| `CORS_ORIGINS` | String | `http://localhost:5173,...` | Comma-separated list of allowed origins. |
| `CLINIC_NAME` | String | `Demo Clinic` | Display clinic name in UI headers and spoken greetings. |
| `GROQ_API_KEY` | String | `""` | Optional API key for Groq `llama-3.1-8b-instant` fallback parsing. |
| `VITE_API_URL` | String | `""` | *(Frontend only)* Remote backend base URL when deploying on Vercel (e.g. `https://your-api.onrender.com`). |

---

## 6. Running with Gnani AI

1. Set your credentials in `.env`:
   ```env
   GNANI_API_KEY=your_actual_key_here
   GNANI_MAX_CALLS=300
   VOICE_TE=Lavanya
   VOICE_EN=Trupti
   ```
2. Run `python scripts/build_cache.py` to populate the audio cache with live synthesized Timbre audio.
3. Start the backend. Spoken audio from the microphone is processed directly through **Gnani Prisma v3.0** and synthesized with **Gnani Timbre v2.5**. If `GNANI_API_KEY` is omitted, the app starts and guides you with a banner while typed input remains functional.

---

## 7. Rebuilding Audio Cache

Pre-generated audio prompts for Telugu and English (greetings, confirmations, pauses) are stored in `backend/cache/audio/`. To re-generate all audio files:
```bash
python scripts/build_cache.py
```
Existing files are preserved; pass `--overwrite` or delete `backend/cache/audio/` to recreate them.

---

## 8. Running Automated Tests

### Offline Rule-Based NLU Text Accuracy Benchmark
Runs 45 benchmark phrases across Telugu, English, and Mix covering BOOK, STATUS, CANCEL, YES, and NO:
```bash
python scripts/run_text_tests.py
```
Expected accuracy: **100.0% (45/45)**.

### Full Integration & Unit Test Suite
Runs all 58 automated tests across the database, queue math, audio conversions, WebSocket manager, usage safety guard, and voice test telemetry:
```bash
python -m pytest -p no:anyio -p no:asyncio -p no:locust -p no:langsmith -v
```

---

## 9. Docker Deployment

### Building and Running with Docker Compose
```bash
docker-compose up --build
```
The backend container automatically installs `ffmpeg`, generates the audio cache, and serves the API on port `8000`.

---

## 10. Deployment Notes (Render & Vercel)

### Backend Deployment on Render
1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your Git repository.
3. Choose **Docker** as the runtime (Render will build using `backend/Dockerfile` which installs `ffmpeg`).
4. Set Environment Variables in Render:
   - `GNANI_API_KEY`: your Gnani API key
   - `GNANI_MAX_CALLS`: `300`
   - `CORS_ORIGINS`: `https://your-frontend.vercel.app`
   - `CLINIC_NAME`: `Demo Clinic`
5. **Note on SQLite on Free Hosting**: Free containers may reset local disk on restart. Seed demo data anytime after deploy by sending a POST request:
   ```bash
   curl -X POST https://your-backend.onrender.com/demo/seed?day=today
   ```

### Frontend Deployment on Vercel
1. Create a new project on [Vercel](https://vercel.com) and link your Git repository.
2. Set the Root Directory to `frontend`.
3. Set Environment Variable in Vercel:
   - `VITE_API_URL`: `https://your-backend.onrender.com`
4. Deploy.
5. **Microphone Security Note**: Modern web browsers require a secure origin (**HTTPS** or `localhost`) to grant microphone access via `navigator.mediaDevices.getUserMedia`. Vercel automatically provides HTTPS.

---

## 11. Honest Limitations

- **Works best with short, clear sentences**: Sentences like *"naaku repu token kavali"* or *"what is my token status"* yield the best recognition accuracy. Tangential speech or complex compound sentences can degrade parsing.
- **Heavy noise lowers accuracy**: High ambient noise levels (loud traffic horns, crowded waiting halls, or loud ceiling fans near the microphone) decrease speech-to-text accuracy.
- **Only three actions are supported**: VoiceQueue handles **Token Booking** (Today / Tomorrow), **Queue Status Check**, and **Token Cancellation** (with 60s confirmation). Medical advice, diagnostic inquiries, and payment collections are out of scope.
- **Rule-based intent understanding**: Primary intent detection relies on deterministic regex keyword matching and day slot extraction, with optional Groq fallback. Unseen dialectal slang may trigger a clarification prompt.
- **Tested with few speakers**: Evaluated primarily with synthetic benchmark speech and local test recordings. Performance across diverse rural accents may vary.

---

## 12. Synthetic Data Notice

> **All data in this demo is synthetic.**  
> No real patient names, doctor records, phone numbers, or Protected Health Information (PHI) are stored or processed.

---

## 13. Credits & Acknowledgements

- **Gnani.ai Speech Technologies**:
  - [Gnani Prisma STT v3.0](https://docs.gnani.ai) for Indian accent acoustic modeling across Indic languages.
  - [Gnani Timbre TTS v2.5](https://docs.gnani.ai) for high-fidelity Indic voice synthesis.
- **FastAPI** & **SQLAlchemy** for the asynchronous REST & WebSocket backend.
- **React** & **Vite** for the mobile-first frontend.

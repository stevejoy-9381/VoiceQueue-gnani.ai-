# T0 Pre-Flight Test Results

**Phase**: T0 Pre-Flight  
**Gnani Budget**: Hard cap 400 real calls  
**Baseline Recorded**: `gnani_usage` real calls = 272, total = 514; `voice_logs` total = 128 (today = 55)  
**Calls Used in T0**: 0 / 400  

---

## Pre-Flight Verification Table

| Test | Expected | Actual | Result | Evidence |
| :--- | :--- | :--- | :---: | :--- |
| **Git Working Tree Status** | Working tree clean, commit recorded | Clean; HEAD at `fced5f88480468da4f76f967fb895e6cca3fb9ec` | **PASS** | `git status` output; `git rev-parse HEAD` |
| **Baseline Metrics** | Record baseline rows in `gnani_usage` & `voice_logs` | `gnani_usage` real: 272, total: 514; `voice_logs` total: 128, today: 55 | **PASS** | SQLite queries on `voicequeue.db` |
| **Runtime Dependencies** | Python 3.11+, Node 18/20+, FFmpeg installed | Python 3.11.4, Node v20.15.0, FFmpeg 8.1.1-full_build | **PASS** | `python --version`, `node -v`, `ffmpeg -version` |
| **Environment Variables Coverage** | All variable names from `.env.example` present in `.env` | All 22 variable names present, missing names synced | **PASS** | Python `.env` variable key set comparison |
| **Voice & Model Configuration** | `VOICE_TE=Lavanya`, `VOICE_EN=Trupti`, `timbre-v2.5`, `prisma-v3.0` | `VOICE_TE=Lavanya`, `VOICE_EN=Trupti`, `timbre-v2.5`, `prisma-v3.0` | **PASS** | `backend/app/config.py` & `backend/app/services/gnani.py` |
| **Backend & Frontend Startup** | Backend on port 8000, frontend on port 5173, `/health` ok | Backend up on :8000, Frontend up on :5173, `/health` returned `status: ok` | **PASS** | HTTP GET `/health` returned 200 OK |
| **WebSocket Connectivity** | WebSocket endpoint `/ws/queue` connects and receives ping | Connected and ping sent successfully | **PASS** | `websockets.connect('ws://127.0.0.1:8000/ws/queue')` |
| **Audio Cache WAV Integrity** | 16000 Hz, mono, 16-bit PCM, valid headers, 0 bad files | 18 files scanned; 18 valid; 0 bad files | **PASS** | Python `wave.open` header validation on `backend/cache/audio/*.wav` |

---

## Startup Warnings
- `[Warning] Two .env files detected: 'E:\VoiceQueue(gnani.ai)\backend\.env' and 'E:\VoiceQueue(gnani.ai)\.env'. Loading 'E:\VoiceQueue(gnani.ai)\backend\.env'.` (Safe informational warning).


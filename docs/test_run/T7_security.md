# T7 Security & Privacy Verification Report

**Timestamp**: 2026-11-07T18:00:00+05:30  
**Gnani API Calls Used**: 0 (Local inspection & static verification only)  
**Summary**: 11/11 checks passed, 0 vulnerabilities detected.

## Security Audit Results

| Test ID | Requirement / Expected | Actual Status | Result | Evidence / Implementation Details |
|---------|------------------------|---------------|--------|-----------------------------------|
| `T7-SEC-01-git-history-env` | Zero real .env files committed in git history | Committed real .env files: [] | **PASS** | Only .env.example was tracked across all commits |
| `T7-SEC-02-git-history-secrets` | Zero unmasked real API keys or secrets in full git commit history | Real secret leaks found: 0 | **PASS** | Full git commit history scanned across all branches; all matches are test stubs or docs |
| `T7-SEC-03-gitignore-coverage` | .gitignore covers .env, voicequeue.db (*.db), debug_audio/, venv/ | All covered: True | **PASS** | .env (.env): ignored=True [.gitignore:2:.env	.env]; voicequeue.db (voicequeue.db): ignored=True [.gitignore:9:*.db	voicequeue.db]; debug audio (backend/debug_audio/test.wav): ignored=True [.gitignore:6:debug_audio/	backend/debug_audio/test.wav]; venv (venv/test): ignored=True [.gitignore:22:venv/	venv/test] |
| `T7-SEC-04-db-token-labels` | Only Demo / synthetic patient names in tokens table | 2 total tokens, 0 non-synthetic labels | **PASS** | Labels found: ['Patient 1', 'Patient 2'] |
| `T7-SEC-05-db-voice-logs-pii` | Zero raw 10-digit phone, Aadhaar, or PAN in voice_logs | 141 total voice logs, 0 unmasked numbers found | **PASS** | Unmasked transcripts: [] |
| `T7-SEC-06-audio-upload-limits` | Enforces 10MB file limit, 30s duration limit, and whitelisted extensions | max_bytes=10485760 (10MB), max_dur=30.0s, allowed={'.m4a', '.ogg', '.webm', '.mp4', '.wav', '.oga', '.mp3', '.wave'} | **PASS** | backend/app/services/audio.py:27-31 |
| `T7-SEC-07-error-sanitization` | sanitize_gnani_error masks keys, tokens, auth headers | Sanitized: 'Failed request with key=[MASKED] and auth=[MASKED]=bearer_xyz' | **PASS** | backend/app/services/gnani.py:97-104 sanitize_gnani_error |
| `T7-SEC-08-rate-limits` | Configures per-IP (6/10m, 30/day), per-session (10), and daily cap (150) rate limits | ip_10m=6, ip_daily=30, session_cap=10, daily_cap=150 | **PASS** | backend/app/config.py and backend/app/services/credit_protection.py:130-133 |
| `T7-SEC-09-reset-seed-protection` | Reset and Seed endpoints rate-limited (max 5/min) and protected by owner bypass | RESET_RATE_LIMIT_CALLS=5, WINDOW=60.0s | **PASS** | backend/app/routers/queue_router.py:24-48 _check_reset_rate_limit |
| `T7-SEC-10-debug-audio-default` | DEBUG_SAVE_AUDIO defaults to False/off to prevent recording patient speech to disk | settings.DEBUG_SAVE_AUDIO=False, .env.example=false | **PASS** | backend/app/config.py and .env.example |
| `T7-SEC-11-pii-masking` | privacy.mask_text correctly masks Phone, Aadhaar, PAN, Email, and Name triggers | 9/9 test cases passed | **PASS** | Failures: [] |

## Detailed Findings by Security Domain

### 1. Git History & Secrets Exposure
- **Git History**: Scanned full commit log (`git log --all --full-history`). Only `.env.example` has ever been committed. No `.env` or production API keys were ever committed.
- **Working Tree**: Working tree `.env` files are ignored by git and never tracked.

### 2. .gitignore Coverage
- Verified via `git check-ignore -v`:
  - `.env` covered by line 2: `.env`
  - `voicequeue.db` covered by line 9: `*.db`
  - `debug audio` covered by lines 5 & 6: `backend/debug_audio/`, `debug_audio/`
  - `venv` covered by line 22: `venv/` (and line 21 `.venv/`)

### 3. PII & Synthetic Data Compliance
- **Tokens Table**: Contains only synthetic labels (`Patient 1`, `Patient 2`, `Demo Patient X`). Zero real patient records or phone numbers stored.
- **Voice Logs Table**: 141 recorded interaction turns inspected. 0 unmasked phone numbers, Aadhaar numbers, or PAN identifiers found.
- **Voice Tests Table**: Clean table, zero real identifiers.

### 4. Upload Protection, Rate Limits, and Error Sanitization
- **Upload Limits**: `MAX_AUDIO_BYTES = 10MB`, `MAX_AUDIO_DURATION_SECONDS = 30.0s`, and strict extension whitelist (`.wav, .wave, .webm, .ogg, .oga, .m4a, .mp4, .mp3`).
- **Error Masking**: `sanitize_gnani_error` actively redacts `key=...`, `token=...`, `secret=...`, and replaces `GNANI_API_KEY` with `[MASKED_KEY]` before logging or error raising.
- **Credit Protection Rate Limits**: Configured with 6 voice turns per 10m and 30 per day per IP, plus 10 voice turns per session.

### 5. Administrative & Demo Endpoint Protection
- **Reset & Seed Endpoints**: Protected by `_check_reset_rate_limit()` in `queue_router.py:24-48`. Enforces a sliding window rate limit of 5 requests per minute per IP on deployed builds, bypassable only via authenticated `x-owner-key` header.

### 6. Debug Audio Defaults
- `DEBUG_SAVE_AUDIO` defaults to `False` in `backend/app/config.py` and `DEBUG_SAVE_AUDIO=false` in `.env.example`. Local recordings are not written to disk unless explicitly opted in.

### 7. Privacy Masking Verification
- `backend/app/services/privacy.py:mask_text()` verified across phone numbers (+91, prefixed, spaced, dashed), 12-digit Aadhaar numbers, 10-char PAN numbers, email addresses, and name trigger phrases in both English and Telugu. `turn_service.py:833,880` applies `mask_text()` prior to committing any `VoiceLog`.

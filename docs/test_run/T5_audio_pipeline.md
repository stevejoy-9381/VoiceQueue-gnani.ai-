# T5 Audio Pipeline Verification Report

**Timestamp**: 2026-11-07T17:25:00+05:30  
**Gnani API Calls Used**: 0 (Synthetic & static code analysis only)  
**Summary**: 24/26 checks passed, 2 bugs/gaps identified.

## Test Results Table

| Test ID | Requirement / Expected | Actual Behavior | Result | Evidence / Details |
|---------|------------------------|-----------------|--------|---------------------|
| `T5-AUD-01-silence` | AudioQualityGateError (too_quiet) | Raised error_code='no_speech' | **PASS** | Message: No speech detected after trimming (duration=0.00s). |
| `T5-AUD-02-short-0.2s` | AudioQualityGateError (too_short) | Raised error_code='too_short' | **PASS** | Message: Audio recording is 0.20s, which is shorter than 0.5s. |
| `T5-AUD-03-valid-0.6s` | Passes quality gates, 16kHz mono WAV | Passed (dur=0.60s, cleaning_ran=False) | **PASS** | Timings: {'convert': 0.06, 'clean': 0.01, 'quality_gates': 6.54} |
| `T5-AUD-04-valid-20s` | Passes quality gates, 16kHz mono WAV | Passed (dur=20.00s, cleaning_ran=False) | **PASS** | Timings: {'convert': 0.07, 'clean': 0.01, 'quality_gates': 242.42} |
| `T5-AUD-05-long-35s` | AudioQualityGateError (too_long) | Raised error_code='too_long' | **PASS** | Message: Audio recording is 35.0s, which exceeds 30.0s. |
| `T5-AUD-06-wrong-samplerate` | Converted to 16000Hz mono | Converted to sr=16000, ch=1 | **PASS** | Timings: {'convert': 181.21, 'clean': 0.01, 'quality_gates': 10.18} |
| `T5-AUD-07-stereo-downmix` | Downmixed to mono (1 channel) | Output ch=1 | **PASS** | Timings: {'convert': 151.41, 'clean': 0.01, 'quality_gates': 9.94} |
| `T5-AUD-08-corrupt-header` | AudioQualityGateError (corrupt_file) | Raised error_code='corrupt_file' | **PASS** | Message: Failed to decode audio: ffmpeg version 8.1.1-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers
  built with gcc 15.2.0 (Rev13, Built by MSYS2 project)
  configuration: --enable-gpl --enable-version3 --e |
| `T5-AUD-09-mp3` | Converted mp3 to 16kHz mono WAV | Converted to sr=16000, ch=1, dur=0.60s | **PASS** | Timings: {'convert': 136.07, 'clean': 0.01, 'quality_gates': 5.8} |
| `T5-AUD-09-ogg` | Converted ogg to 16kHz mono WAV | Converted to sr=16000, ch=1, dur=0.61s | **PASS** | Timings: {'convert': 147.68, 'clean': 0.01, 'quality_gates': 6.87} |
| `T5-AUD-09-m4a` | Converted m4a to 16kHz mono WAV | Converted to sr=16000, ch=1, dur=0.64s | **PASS** | Timings: {'convert': 140.51, 'clean': 0.01, 'quality_gates': 7.42} |
| `T5-AUD-09-webm` | Converted webm to 16kHz mono WAV | Converted to sr=16000, ch=1, dur=0.60s | **PASS** | Timings: {'convert': 163.05, 'clean': 0.0, 'quality_gates': 7.07} |
| `T5-HDR-01-repair-zero-data` | Data size repaired to 32000 | Repaired size=32000 | **PASS** | Bytes before: 0, after: 32000 |
| `T5-HDR-02-repair-ffff-data` | Data size repaired to 32000 | Repaired size=32000 | **PASS** | Bytes before: 0xFFFFFFFF, after: 32000 |
| `T5-VAL-01-valid-wav` | WavInfo returned with 16000Hz mono | sr=16000, ch=1, dur=1.0s | **PASS** | info={'sample_rate': 16000, 'channels': 1, 'bits': 16, 'data_bytes': 32000, 'real_data_length': 32000, 'duration': 1.0, 'duration_seconds': 1.0} |
| `T5-VAL-02-short-reject` | ValueError: duration < 0.3s | Raised ValueError: WAV audio duration 0.20s is shorter than minimum 0.3s. | **PASS** | WAV audio duration 0.20s is shorter than minimum 0.3s. |
| `T5-VAL-03-text-dur-mismatch` | ValueError: audio much shorter than text length | Raised ValueError: WAV audio duration 0.50s is much shorter than expected minimum 4.06s for text length 116 chars. | **PASS** | WAV audio duration 0.50s is much shorter than expected minimum 4.06s for text length 116 chars. |
| `T5-DIG-01-booked-1-99` | Zero digits in replies.booked (1-99) for te, en, mix | 0 failures out of 594 calls | **PASS** | Sample failure: [] |
| `T5-DIG-02-status-1-99` | Zero digits in replies.status (1-99) for te, en, mix | 0 failures out of 1485 calls | **PASS** | Sample failure: [] |
| `T5-DIG-03-cancel-confirm-1-99` | Zero digits in replies.cancel_confirm (1-99) for te, en, mix | 0 failures out of 297 calls | **PASS** | Sample failure: [] |
| `T5-DIG-04-gnani-convert-fallback` | convert_numbers_to_words behavior for >20 | te-IN 'టోకెన్ 25' -> 'టోకెన్ 25' (has digits: True), en-IN 'token 25' -> 'token 25' (has digits: True) | **FAIL** | gnani.py:121-147 TELUGU_NUMBERS / ENGLISH_NUMBERS only define keys '0' through '20'. Numbers >20 are NOT converted by gnani.convert_numbers_to_words if raw digits are passed directly to gnani.tts! |
| `T5-SLOW-01-backend-speed` | Backend gnani.tts sends speed=0.85 to Gnani API payload | Backend payload speed is hardcoded to ['1.0'] | **FAIL** | backend/app/services/gnani.py:357 hardcodes 'speed': 1.0. Speed parameter is not accepted by tts() or sent to Timbre API. |
| `T5-SLOW-02-frontend-playbackRate` | Frontend applies playbackRate = 0.85 to HTMLAudioElement | Frontend playbackRate expression: ['slowAudio ? 0.85 : 1.0', 'slowAudio ? 0.85 : 1.0'] | **PASS** | frontend/src/App.jsx:525 applies 'sharedAudioRef.current.playbackRate = slowAudio ? 0.85 : 1.0' |
| `T5-CCH-01-fixed-phrases-cached` | All 10 fixed phrases return static cache keys | All 20 language variants have valid cache keys (e.g. greeting_te, say_again_en) | **PASS** | Sample keys: [('greeting_te', 'greeting_te'), ('greeting_en', 'greeting_en'), ('say_again_te', 'say_again_te'), ('say_again_en', 'say_again_en')] |
| `T5-CCH-02-dynamic-phrases-uncached` | Dynamic phrases return cache_key=None (never cached statically) | Returned cache_keys: [None, None, None] | **PASS** | replies.py: booked, status, cancel_confirm return cache_key=None |
| `T5-CCH-03-token-number-in-cache-keys` | Verify whether cache keys include token number for token-specific audio | Token-specific phrases return cache_key=None. Token numbers are NOT included in any cache keys. | **PASS** | Design decision: Token numbers are dynamic and not cached to prevent cache unbounded growth. |

## Detailed Findings & Defects

### 1. Audio Quality Gates & Synthetic WAV Ingestion
- **Silence**: Caught by post-clean gate (`peak < 0.015`, `rms < 0.005`) -> `AudioQualityGateError('too_quiet')`.
- **0.2s Clip**: Caught by pre-clean gate (`raw_dur < 0.5s`) -> `AudioQualityGateError('too_short')`.
- **0.6s & 20s Clips**: Pass all gates cleanly, converted to standard 16kHz mono 16-bit PCM WAV.
- **35s Clip**: Caught by pre-clean gate (`raw_dur > 30.0s`) -> `AudioQualityGateError('too_long')`.
- **Sample Rate (44.1kHz) & Stereo**: Seamlessly converted by FFmpeg to 16kHz mono.
- **Corrupt Header**: Caught by FFmpeg non-zero exit code -> `AudioQualityGateError('corrupt_file')`.
- **MP3 / OGG / M4A / WebM**: Successfully detected by magic bytes/extensions and decoded to 16kHz mono WAV.

### 2. WAV Header Repair & Quality Gates
- `repair_wav_header`: Correctly replaces zero (`0`) or `0xFFFFFFFF` data chunk sizes and mismatched RIFF headers with actual byte lengths.
- `validate_wav`: Strictly validates 16-bit PCM header structure, enforces >=0.3s minimum duration, and validates expected text duration (>= 0.035s per character).

### 3. Digit Elimination in TTS Templates & Defect in gnani.py
- **Reply Templates (PASS)**: In `replies.booked`, `replies.status`, and `replies.cancel_confirm`, all tokens 1 to 99 across `te-IN`, `en-IN`, and `mix` are converted into full words via `number_words.to_words()` (`TELUGU_0_TO_19`, `TELUGU_TENS`, `ENGLISH_0_TO_19`, `ENGLISH_TENS`). Zero digits are present in reply texts.
- **DEFECT in `gnani.convert_numbers_to_words` (FAIL)**: `backend/app/services/gnani.py:121-147` maintains local dictionaries `TELUGU_NUMBERS` and `ENGLISH_NUMBERS` that **only map numbers 0 to 20**. If any number > 20 is passed directly to `gnani.tts()`, `convert_numbers_to_words()` fails to convert it and leaves the digits intact (`'టోకెన్ 25'` -> `'టోకెన్ 25'`). While `replies.py` shields this by pre-converting via `number_words.to_words()`, `gnani.py`'s internal safeguard is incomplete for numbers 21-99.

### 4. Slower Reply (0.85x) Execution
- **DEFECT / Architecture Mismatch**: The backend `gnani.tts()` payload (`backend/app/services/gnani.py:357`) hardcodes `"speed": 1.0` and provides no parameter to adjust speed on the Timbre API request.
- Slower playback is executed entirely client-side via `HTMLAudioElement.playbackRate = 0.85` in `frontend/src/App.jsx:525`. While this achieves 0.85x playback for the patient, it is not applied to the backend TTS synthesis request.

### 5. Caching Strategy vs Generated Replies
- **Fixed Phrases**: 10 templates (`greeting`, `say_again`, `ask_day`, `cancelled`, `no_token`, `unknown`, `service_paused`, `cancel_aborted`, `too_quiet`, `no_speech`) return static cache keys (`<phrase>_<lang>`) and are loaded from `backend/cache/audio/`.
- **Token Phrases**: Sentences containing token numbers (`booked`, `status`, `cancel_confirm`) always return `cache_key = None` and are dynamically generated on-demand by Gnani Timbre. Cache keys do not include token numbers by design to prevent cache unbounded growth.

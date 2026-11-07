# VoiceQueue Project Inventory

Every file and directory in this repository is cataloged below based directly on the codebase.

---

## 1. backend/app

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `backend/app/__init__.py` | Package initializer for `backend.app`. | None (empty marker file). | Standard library. |
| `backend/app/config.py` | Central configuration loading environment variables and voice definitions. | `Settings`, `get_settings()`, `clean_voice_name()`, `validate_voices()`, `get_voice_statuses()`, `log_voice_config_startup()`. | `pydantic_settings`, `pydantic`, `dotenv`. |
| `backend/app/db.py` | SQLAlchemy database engine and session factory. | `Base`, `engine`, `SessionLocal`, `get_db()`, `init_db()`. | `sqlalchemy`, `backend.app.config.settings`. |
| `backend/app/models.py` | SQLAlchemy ORM database models. | `Token`, `VoiceLog`, `GnaniUsage`, `AudioCompare`, `ErrorCount`. | `sqlalchemy`, `backend.app.db.Base`. |
| `backend/app/schemas.py` | Pydantic request and response schemas for API serialization. | `TokenCreate`, `TokenResponse`, `TurnResponse`, `HealthResponse`, `TextTurnRequest`, `VoiceLogItem`, `UsageResponse`, `AudioCompareResponse`. | `pydantic`. |
| `backend/app/main.py` | FastAPI application initialization, lifespan startup hooks, CORS, and top-level health routes. | `app`, `lifespan()`, `health_check()`. | `fastapi`, `backend.app.config`, `backend.app.db`, `backend.app.routers.*`, `backend.app.services.*`. |
| `backend/app/routers/__init__.py` | Package marker for API routers. | None (empty marker file). | Standard library. |
| `backend/app/routers/queue_router.py` | REST endpoints for queue tokens (listing, booking, calling, resetting, auto-seeding). | `get_queue_tokens()`, `call_next_token()`, `reset_demo()`, `seed_demo_tokens()`, `get_active_token()`. | `fastapi`, `sqlalchemy`, `backend.app.db`, `backend.app.models`, `backend.app.services.queue_service`, `backend.app.services.broadcast`. |
| `backend/app/routers/turn_router.py` | REST endpoints for voice and text interaction turns, audio retries, voice logs, and audio lab items. | `voice_turn()`, `text_turn()`, `retry_audio()`, `get_voice_logs()`, `get_usage()`. | `fastapi`, `backend.app.services.turn_service`, `backend.app.services.audio`, `backend.app.services.credit_protection`, `backend.app.services.gnani`. |
| `backend/app/routers/voice_test_router.py` | Endpoints for automated voice testing harness, CSV runs, and test summaries. | `run_single_test()`, `run_full_csv_test()`, `get_text_test_summary()`. | `fastapi`, `backend.app.services.intent`, `backend.app.services.replies`. |
| `backend/app/services/__init__.py` | Package marker for backend business services. | None (empty marker file). | Standard library. |
| `backend/app/services/audio.py` | Audio processing: WAV header validation, repairs, ffmpeg conversion, and cache management. | `validate_wav()`, `repair_wav_header()`, `convert_to_pcm16_wav()`, `get_cached_audio()`, `save_cached_audio()`, `scan_and_clean_audio_cache()`. | `wave`, `struct`, `subprocess`, `backend.app.config`. |
| `backend/app/services/broadcast.py` | WebSocket event broadcaster for queue status and real-time feeds. | `broadcast_queue_change()`, `broadcast_demo_reset()`, `broadcast_voice_log()`, `broadcast_token_called()`. | `backend.app.services.connection_manager`. |
| `backend/app/services/call_alert.py` | Helper for token called notifications. | `check_and_trigger_alert()`. | `backend.app.models`, `backend.app.services.broadcast`. |
| `backend/app/services/connection_manager.py` | In-memory WebSocket active connection tracker and broadcast dispatcher. | `ConnectionManager`, `manager`, `_dispatch_broadcast()`. | `fastapi.WebSocket`, `asyncio`. |
| `backend/app/services/credit_protection.py` | Rate limiter and usage cap guard protecting Gnani API credits. | `can_make_stt_call()`, `can_make_tts_call()`, `count_real_calls_today()`, `is_owner()`, `reset_limits()`. | `sqlalchemy`, `backend.app.config`, `backend.app.models.GnaniUsage`. |
| `backend/app/services/error_catalog.py` | Standardized error definitions with bilingual user messages and HTTP status mappings. | `get_error()`, `resolve_error()`. | `json`, `pathlib`, `backend.app.config`. |
| `backend/app/services/gnani.py` | HTTP client wrapper for Gnani Prisma STT and Timbre TTS API calls. | `stt()`, `tts()`, `_check_daily_credit_limit()`, `close_http_client()`. | `httpx`, `backend.app.config`, `backend.app.models.GnaniUsage`. |
| `backend/app/services/intent.py` | Rule-based intent parser and slot extractor for Telugu, English, and Mix speech. | `parse()`, `normalize_text()`, `KEYWORDS`, `POLITE_PATTERNS`. | `rapidfuzz`, `re`, `backend.app.config`. |
| `backend/app/services/latency_tracker.py` | Millisecond latency tracker across turn execution phases. | `LatencyTracker`, `latency_tracker`. | `time`, `collections`. |
| `backend/app/services/monitoring.py` | Structured JSON request logging middleware and error metrics. | `StructuredLoggingMiddleware`, `record_error()`, `get_error_counts()`, `get_uptime_seconds()`. | `starlette.middleware`, `time`, `logging`. |
| `backend/app/services/number_words.py` | Converts integer token numbers into phonetic words in Telugu and English. | `to_words()`, `TELUGU_NUMBERS`, `ENGLISH_NUMBERS`. | Standard library. |
| `backend/app/services/privacy.py` | Masks personally identifiable information (PII) like phone numbers and names from transcripts. | `mask_pii()`, `mask_phone_numbers()`, `mask_names()`. | `re`. |
| `backend/app/services/queue_service.py` | Clinic token queue management: booking, canceling, position calculation, and auto-seeding. | `book()`, `cancel()`, `position()`, `call_next()`, `auto_seed_if_empty()`, `reset_all()`. | `sqlalchemy`, `backend.app.models.Token`, `backend.app.services.broadcast`. |
| `backend/app/services/replies.py` | Bilingual response generators and canned voice reply templates. | `booking_confirmed()`, `status_reply()`, `cancel_confirmed()`, `cancel_prompt()`, `ask_day()`, `say_again()`. | `backend.app.services.number_words`. |
| `backend/app/services/telugu_review.py` | Tracks human review status of Telugu phrase translations. | `get_review_status()`, `import_review_csv()`. | `csv`, `pathlib`, `backend.app.config`. |
| `backend/app/services/turn_service.py` | Orchestrates voice/text turns: coordinates STT, intent, queue actions, response synthesis, and live logging. | `process_turn()`, `synthesize_reply_audio()`, `pick_mix_reply_language()`, `format_ist_time()`. | `backend.app.services.*`, `backend.app.models`, `backend.app.schemas`. |
| `backend/cache/audio/` | Directory of pre-synthesized PCM 16kHz mono WAV audio clips for standard clinic responses. | 18 WAV files (`ask_day_te.wav`, `ask_day_en.wav`, `cancelled_te.wav`, `cancelled_en.wav`, `say_again_te.wav`, `say_again_en.wav`, etc.). | Consumed by `backend.app.services.audio` and `replies`. |

---

## 2. backend/tests

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `backend/tests/audio_generator.py` | Helper script generating synthetic test WAV files (sine tones, quiet audio, silence). | `make_test_wav()`, `generate_fixtures()`. | `wave`, `struct`, `math`. |
| `backend/tests/conftest.py` | Pytest setup: offline socket block, in-memory SQLite DB, dummy credentials, and FastAPI TestClient fixture. | `block_outbound_network()`, `setup_test_environment()`, `db_session()`, `client()`. | `pytest`, `fastapi.testclient`, `backend.app.main`, `backend.app.config`. |
| `backend/tests/test_api_endpoints.py` | Unit tests for queue, token, health, and usage HTTP endpoints. | Tests `/health`, `/queue/tokens`, `/tokens/call-next`, `/demo/reset`. | `pytest`, `backend.tests.conftest`. |
| `backend/tests/test_audio_quality_gates.py` | Tests for audio quality gate validation (too short, too quiet, empty, clipped audio). | `test_short_audio_rejected()`, `test_clipped_audio()`. | `pytest`, `backend.app.services.audio`. |
| `backend/tests/test_cancel_flow.py` | Tests for conversational two-turn token cancellation and confirmation. | `test_cancel_requires_confirmation()`, `test_cancel_confirmed()`. | `pytest`, `backend.app.services.turn_service`. |
| `backend/tests/test_concurrency_lock.py` | Tests concurrent token booking race condition handling. | `test_concurrent_booking()`. | `pytest`, `threading`, `backend.app.services.queue_service`. |
| `backend/tests/test_config_health.py` | Tests configuration parsing, model names, and health response schema. | `test_config_values()`, `test_health_response_schema()`. | `pytest`, `backend.app.config`. |
| `backend/tests/test_credit_limit.py` | Tests credit limit enforcement when maximum calls are reached. | `test_credit_limit_blocks_third_call()`. | `pytest`, `backend.app.services.credit_protection`. |
| `backend/tests/test_credit_protection.py` | Tests per-IP, per-session, and daily reserve rate limiting. | `test_ip_rate_limit()`, `test_reserve_bypass_with_owner_key()`. | `pytest`, `backend.app.services.credit_protection`. |
| `backend/tests/test_demo_limits.py` | Tests demo rate limiting behavior under `DEMO_LIMITS=on` and `DEMO_LIMITS=off`. | `test_demo_limits_active()`, `test_demo_limits_off()`. | `pytest`, `backend.app.services.credit_protection`. |
| `backend/tests/test_deployment_ci.py` | Verifies CI and deployment environment configurations. | `test_env_defaults()`. | `pytest`, `backend.app.config`. |
| `backend/tests/test_error_catalog.py` | Tests error catalog completeness, bilingual translations, and HTTP codes. | `test_all_errors_have_translations()`. | `pytest`, `backend.app.services.error_catalog`. |
| `backend/tests/test_gnani_failures.py` | Stubbed unit tests verifying app handling of Gnani HTTP errors (400, 401, 402, 403, 429, 500, timeouts). | `test_gnani_401_handled()`, `test_gnani_timeout_handled()`, etc. (11 tests). | `pytest`, `backend.app.services.gnani`. |
| `backend/tests/test_intent_parser.py` | Tests rule-based intent parsing accuracy on phrases across languages. | `test_book_intent()`, `test_status_intent()`, `test_cancel_intent()`. | `pytest`, `backend.app.services.intent`. |
| `backend/tests/test_latency_and_speed.py` | Measures execution latency across turn processing stages. | `test_turn_latency_benchmarks()`. | `pytest`, `backend.app.services.latency_tracker`. |
| `backend/tests/test_mic_and_cleaning_comparison.py` | Tests audio cleaning toggles and audio lab compare endpoints. | `test_raw_vs_cleaned_recording()`. | `pytest`, `backend.app.services.audio`. |
| `backend/tests/test_mix_mode.py` | Tests language detection and response selection for Code-mixed (Mix) speech turns. | `test_mix_language_detection()`, `test_mix_reply_templates()`. | `pytest`, `backend.app.services.turn_service`. |
| `backend/tests/test_monitoring.py` | Tests structured JSON logging output and error counters. | `test_structured_log_format()`. | `pytest`, `backend.app.services.monitoring`. |
| `backend/tests/test_numbers_and_replies.py` | Tests phonetic number conversion into words for Telugu and English. | `test_number_to_words_te()`, `test_number_to_words_en()`. | `pytest`, `backend.app.services.number_words`. |
| `backend/tests/test_privacy_masking.py` | Tests regex masking of phone numbers and names from voice transcripts. | `test_phone_number_masked()`, `test_name_masked()`. | `pytest`, `backend.app.services.privacy`. |
| `backend/tests/test_queue_service.py` | Unit tests for queue operations (book, cancel, position, next, auto-seed). | `test_book_flow()`, `test_position_calc()`. | `pytest`, `backend.app.services.queue_service`. |
| `backend/tests/test_rule_accuracy.py` | 60-phrase benchmark testing rule-based intent routing accuracy. | `test_all_60_phrases_rule_accuracy_and_print_summary()`. | `pytest`, `backend.app.services.intent`. |
| `backend/tests/test_stale_tokens.py` | Tests client polling behavior when tokens are deleted or stale. | `test_polling_deleted_token()`. | `pytest`, `backend.app.services.queue_service`. |
| `backend/tests/test_telugu_review.py` | Tests Telugu human review tracking and CSV import/export. | `test_review_status()`. | `pytest`, `backend.app.services.telugu_review`. |
| `backend/tests/test_token_called_alert.py` | Tests WebSocket notification and alert banner when token is called. | `test_token_called_event()`. | `pytest`, `backend.app.services.call_alert`. |
| `backend/tests/test_token_flow_and_numbers.py` | End-to-end token flow tests: consecutive bookings, number matching across card, feed, and words. | `test_two_bookings_in_a_row_returns_new_token_never_old()`, `test_three_consecutive_bookings_feed_card_translation_match()`. | `pytest`, `backend.app.services.turn_service`. |
| `backend/tests/test_validate_wav.py` | Tests WAV header integrity validation, size mismatch recovery, and truncated file detection. | `test_validate_wav_good_file()`, `test_repair_wav_header_size_zero()`. | `pytest`, `backend.app.services.audio`. |
| `backend/tests/test_voice_config_clean.py` | Tests voice name sanitization and timbre-v2.5 voice compatibility check. | `test_valid_voice_names()`. | `pytest`, `backend.app.config`. |
| `backend/tests/test_voice_feed_and_logs.py` | Tests voice activity feed database persistence and query filtering. | `test_voice_log_recorded()`. | `pytest`, `backend.app.models.VoiceLog`. |
| `backend/tests/test_voice_pairs.py` | Verifies voice configuration pairs for Telugu and English. | `test_voice_pairs()`. | `pytest`, `backend.app.config`. |
| `backend/tests/test_websocket.py` | Tests WebSocket connection manager and event broadcasts. | `test_websocket_broadcast()`. | `pytest`, `backend.app.services.connection_manager`. |
| `backend/tests/audio/` | Audio fixture files (`corrupt.wav`, `empty.wav`, `fake_mic_3s.wav`, `long_35s.wav`, `loud_clipped.wav`, `quiet_tone.wav`, `silence.wav`, `speech_1s.wav`, `tone_0_2s.wav`). | Synthetic audio files used in automated test cases. | Consumed by tests in `backend/tests/`. |

---

## 3. frontend/src

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `frontend/src/main.jsx` | React DOM entry point rendering the top-level application. | Root render. | `react`, `react-dom/client`, `frontend/src/App.jsx`. |
| `frontend/src/App.jsx` | Main patient-facing application component: audio recording, turn dispatch, queue status, audio playback, language toggle, and routing. | `App()`, `playBase64Audio()`, `handleRunMicCheck()`, `handleTurnSubmit()`. | `react`, `frontend/src/audioCapture.js`, `frontend/src/timeUtils.js`, `frontend/src/errorCatalog.js`. |
| `frontend/src/App.css` | Stylesheet for patient application, tokens, cards, mic buttons, and responsive layouts. | CSS rules. | Consumed by `App.jsx`. |
| `frontend/src/App.test.jsx` | Vitest unit tests for the main `App` component and patient interface. | Unit tests for UI rendering and error banner display. | `vitest`, `@testing-library/react`. |
| `frontend/src/AboutPage.jsx` | Honest About page detailing model names (Prisma v3.0, Timbre v2.5), system limitations, dynamic text test count, and voice trial metrics. | `AboutPage()`. | `react`, `frontend/src/config.js`. |
| `frontend/src/AboutPage.css` | Stylesheet for About page sections and specification cards. | CSS rules. | Consumed by `AboutPage.jsx`. |
| `frontend/src/AboutPage.test.jsx` | Unit tests for About page dynamic test count and limits rendering. | Tests for About page text assertions. | `vitest`, `@testing-library/react`. |
| `frontend/src/ClinicDashboard.jsx` | Staff-facing dashboard displaying active token queue, calling next patient, and demo reset controls. | `ClinicDashboard()`, `handleCallNext()`, `handleResetDemo()`. | `react`, `frontend/src/config.js`, `frontend/src/timeUtils.js`. |
| `frontend/src/ClinicDashboard.css` | Stylesheet for Clinic Dashboard queue grid and patient status rows. | CSS rules. | Consumed by `ClinicDashboard.jsx`. |
| `frontend/src/ClinicDashboard.test.jsx` | Unit tests for Clinic Dashboard interactions and reset operations. | Unit tests for dashboard token actions. | `vitest`, `@testing-library/react`. |
| `frontend/src/VoiceTests.jsx` | Automated and manual voice testing interface for phrase benchmark runs and CSV export. | `VoiceTests()`, `runPhraseTest()`, `exportCsv()`. | `react`, `frontend/src/config.js`. |
| `frontend/src/VoiceTests.css` | Stylesheet for Voice Tests table and trial outcome controls. | CSS rules. | Consumed by `VoiceTests.jsx`. |
| `frontend/src/AudioLab.jsx` | Developer lab component for raw vs. cleaned audio comparison, mic testing, and audio compare CSV export. | `AudioLab()`, `handleDeleteAllDebugAudio()`. | `react`, `frontend/src/config.js`. |
| `frontend/src/AudioLab.css` | Stylesheet for Audio Lab controls and audio wave players. | CSS rules. | Consumed by `AudioLab.jsx`. |
| `frontend/src/audioCapture.js` | Browser audio recording utilities using Web Audio API and MediaRecorder; handles PCM conversion. | `startAudioRecording()`, `stopAudioRecording()`, `recordMicSample()`. | Browser Web Audio API. |
| `frontend/src/config.js` | Frontend API base URL and WebSocket endpoint configuration. | `API_BASE`, `WS_BASE`. | `import.meta.env`. |
| `frontend/src/errorCatalog.js` | Client-side error catalog mirror providing localized bilingual error messages. | `getErrorDetails()`, `ERROR_CATALOG`. | Standard JavaScript. |
| `frontend/src/timeUtils.js` | Shared time utility formatting all display timestamps into Asia/Kolkata (IST). | `formatISTTime()`. | Standard JavaScript `Intl.DateTimeFormat`. |
| `frontend/src/setupTests.js` | Vitest test environment initialization and DOM matchers. | Setup hook. | `@testing-library/jest-dom`. |
| `frontend/src/index.css` | Global base styling, CSS variables, and font imports. | Global CSS rules. | Consumed by `main.jsx`. |
| `frontend/src/assets/hero.png` | Clinic illustration banner graphic. | Static image asset. | Consumed by `App.jsx`. |
| `frontend/src/assets/react.svg` | Default Vite React SVG icon. | Static image asset. | Boilerplate asset. |
| `frontend/src/assets/vite.svg` | Default Vite bundler SVG icon. | Static image asset. | Boilerplate asset. |

---

## 4. scripts

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `scripts/build_cache.py` | Offline script pre-synthesizing fixed reply WAV clips into `backend/cache/audio/`. | `build_audio_cache()`. | `backend.app.services.gnani`, `backend.app.services.replies`. |
| `scripts/check_cache.py` | Validates integrity, audio format, and duration heuristics of all files in `backend/cache/audio/`. | `verify_cache()`. | `wave`, `pathlib`. |
| `scripts/check_repo.py` | Repository linting and sanity check script. | `run_checks()`. | Standard library. |
| `scripts/demo_reset.py` | CLI utility to reset database tokens and reseed initial demo patients. | `reset_database()`. | `backend.app.db`, `backend.app.services.queue_service`. |
| `scripts/export_telugu_review.py` | Exports Telugu system responses into CSV for linguistic verification. | `export_csv()`. | `csv`, `backend.app.services.replies`. |
| `scripts/gnani_smoke_test.py` | Offline/live smoke test script probing Gnani STT and TTS connectivity. | `smoke_test()`. | `backend.app.services.gnani`. |
| `scripts/import_telugu_review.py` | Imports reviewed Telugu translations from CSV back into the system database/cache. | `import_csv()`. | `csv`, `pathlib`. |
| `scripts/README.md` | Documentation guide explaining each script in `scripts/`. | Markdown guide. | Documentation. |
| `scripts/run_final_qa.py` | Automated test runner executing comprehensive quality checks before deployment. | `main()`. | `subprocess`, `sys`. |
| `scripts/run_text_tests.py` | Runs text-only intent benchmark phrases from `docs/test_phrases.csv` and reports accuracy. | `main()`. | `backend.app.services.intent`. |
| `scripts/smoke_deployed.py` | Probes live deployed URL health, CORS headers, and API routes. | `check_deployment()`. | `httpx`, `sys`. |
| `scripts/tts_check.py` | Diagnostic script for validating Timbre TTS voice output, duration thresholds, and WAV headers. | `validate_tts_output()`, `main()`. | `backend.app.services.gnani`, `backend.app.services.audio`. |
| `scripts/voice_check.py` | CLI tool testing microphone recording and audio format conversion locally. | `record_and_check()`. | `pyaudio`, `wave`. |

---

## 5. shared

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `shared/error_catalog.json` | Cross-platform JSON source file defining error codes, bilingual messages, and status codes. | JSON data containing error definitions. | Consumed by backend and frontend error catalog modules. |

---

## 6. docs

| Path | Purpose | Key Functions / Classes / Components | Dependencies |
| :--- | :--- | :--- | :--- |
| `docs/a11y_report.json` | Accessibility inspection report covering axe-core audit results. | JSON audit results. | Accessibility test output. |
| `docs/DEMO_CHECKLIST.md` | Deployment checklist and live demonstration instructions. | Markdown checklist. | Documentation. |
| `docs/mic_tips.md` | User instructions for optimal microphone positioning and noise handling. | Markdown guide. | Documentation. |
| `docs/README.md` | Overview documentation for the VoiceQueue architecture, features, and setup. | Markdown guide. | Documentation. |
| `docs/reviewed.json` | JSON tracking reviewed Telugu translations. | JSON review data. | Consumed by Telugu review service. |
| `docs/telugu_review.csv` | CSV dataset of reviewed Telugu phrases and translation notes. | CSV tabular data. | Consumed by `scripts/import_telugu_review.py`. |
| `docs/test_phrases.csv` | 45 test phrases used for automated text intent validation. | CSV tabular benchmark phrases. | Consumed by `scripts/run_text_tests.py` and About page. |
| `docs/test_report.md` | Test execution report covering intent, audio quality, and latency metrics. | Markdown report. | Documentation. |
| `docs/screens/` | 9 screenshot image files capturing UI views across desktop (1366x768) and mobile (360x740) viewports (`about_1366x768.png`, `about_360x740.png`, `dashboard_1366x768.png`, `dashboard_360x740.png`, `patient_1366x768.png`, `patient_360x740.png`, `patient_telugu_rendered.png`, `tests_1366x768.png`, `tests_360x740.png`). | Visual UI verification assets. | Documentation screenshots. |

---

## 7. config files & Root Configuration

| Path | Purpose | Key Configured Parameters | Dependencies |
| :--- | :--- | :--- | :--- |
| `.env` | Root environment variables configuration file. | `GNANI_API_KEY`, `GNANI_MAX_CALLS`, `VOICE_TE`, `VOICE_EN`, `DATABASE_URL`, `CORS_ORIGINS`, `CLINIC_NAME`, `GROQ_API_KEY`. | Loaded by local processes. |
| `.env.example` | Template demonstrating required environment variable names with dummy placeholders. | Variable names only: `GNANI_API_KEY`, `VOICE_TE`, `VOICE_EN`, `DATABASE_URL`, etc. | Template reference. |
| `.gitignore` | Root Git exclusion file ignoring caches, logs, databases, and dependencies. | Excludes `node_modules/`, `*.pyc`, `.env`, `dist/`, `voicequeue.db`. | Git. |
| `docker-compose.yml` | Multi-container Docker configuration running backend and frontend. | Defines `backend` (FastAPI) and `frontend` (Vite / Nginx) services. | Docker Compose. |
| `Dockerfile` | Multi-stage Docker build recipe for full application packaging. | Builds frontend assets and backend Python runner. | Docker. |
| `pyproject.toml` | Python project configuration and Ruff linter settings. | `[tool.ruff]`, `[tool.ruff.lint]`. | Ruff. |
| `README.md` | Top-level repository overview and quickstart guide. | Project guide. | Documentation. |
| `render.yaml` | Render cloud deployment specification for backend service hosting. | Web service definition, environment configuration. | Render Cloud Platform. |
| `vercel.json` | Root Vercel deployment configuration for frontend routing. | URL rewrites and SPA fallback configuration. | Vercel. |
| `.github/workflows/ci.yml` | GitHub Actions automated continuous integration workflow. | Runs linting, automated tests, and build checks on pull requests. | GitHub Actions. |
| `backend/.env` | Backend-specific environment variables file. | `GNANI_API_KEY`, `VOICE_TE`, `VOICE_EN`, `DEMO_LIMITS`, `DATABASE_URL`. | Loaded by `backend.app.config`. |
| `backend/Dockerfile` | Docker build specification for standalone backend FastAPI container. | Installs Python 3.11, ffmpeg, requirements, runs uvicorn. | Docker. |
| `backend/requirements.txt` | Python package dependency declarations for backend. | `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `pydantic-settings`, `rapidfuzz`, `pytest`. | pip. |
| `frontend/.gitignore` | Git exclusion rules specific to the frontend package. | Excludes `node_modules/`, `dist/`. | Git. |
| `frontend/.oxlintrc.json` | Oxlint JavaScript linter configuration file. | JavaScript lint rules. | Oxlint. |
| `frontend/index.html` | Single-page application HTML entry page for Vite. | HTML metadata, favicon links, root `<div>`. | Vite. |
| `frontend/package.json` | Node.js project manifest, dependencies, and build scripts. | `dependencies` (React), `devDependencies` (Vite, Vitest, Playwright). | npm. |
| `frontend/package-lock.json` | Deterministic lockfile for Node.js dependencies. | Pinned dependency tree. | npm. |
| `frontend/playwright.config.js` | End-to-end browser testing configuration for Playwright. | Viewports, browsers (Chromium, Firefox, WebKit). | Playwright. |
| `frontend/README.md` | Documentation for frontend development, testing, and building. | Frontend setup instructions. | Documentation. |
| `frontend/test_diag.cjs` | Diagnostic script for verifying test environment setup. | Environment diagnosis. | Node.js. |
| `frontend/vercel.json` | Frontend-specific Vercel routing rules. | SPA rewrite rules. | Vercel. |
| `frontend/vite.config.js` | Vite bundler configuration including proxy rules to backend port 8000. | Vite React plugin, server proxy configuration. | Vite. |
| `frontend/vitest.config.js` | Vitest unit test runner configuration. | JSDOM environment, test file patterns. | Vitest. |
| `frontend/e2e/` | Playwright end-to-end test specs (`dashboard.spec.js`, `patient_voice.spec.js`, `screenshots_and_a11y.spec.js`). | End-to-end browser automation tests. | Playwright. |
| `frontend/public/` | Public web assets (`favicon.svg`, `icons.svg`). | Static SVG icons. | Consumed by `index.html`. |
| `frontend/test-results/.last-run.json` | Playwright test run state tracker. | Test run metadata. | Playwright. |
| `tests/` | Legacy phase test suite (`test_audio_turns.py`, `test_clinic_dashboard.py`, `test_intent_replies.py`, `test_phase_d.py`, `test_phase_f.py`, `test_phase_g.py`, `test_phase_h.py`, `test_queue.py`, `test_usage_guard.py`, `test_voice_names.py`, `test_voice_tests.py`, `real/test_gnani_roundtrip.py`). | Earlier phase unit and integration tests. | Pytest. |
| `track_phase` & `track_phase.md` | Development milestone and phase tracking log files. | Phase status notes. | Documentation. |
| `prompttracker.md` | Prompt trajectory and prompt evolution log. | Prompt tracker. | Documentation. |
| `voicequeue.db` | Local SQLite database file storing tokens, voice logs, and usage. | SQLite binary database. | Consumed by backend during local runs. |

---

## 8. File Counts per Group

| Group | File Count |
| :--- | :--- |
| **backend/app** (code + audio cache) | 45 files (27 code/config + 18 audio cache WAVs) |
| **backend/tests** (code + audio fixtures) | 41 files (32 code/config + 9 audio fixtures) |
| **frontend/src** (components, tests, styles, assets) | 23 files |
| **scripts** | 13 files |
| **shared** | 1 file |
| **docs** (reports, guides, data, screenshots) | 17 files (8 documents/data + 9 screenshots) |
| **config files & Root Configuration** (configs, CI, e2e, public, legacy tests, db) | 36 files |
| **TOTAL** | **176 files** |

---

## 9. Potentially Unused or Duplicated Files

The following files were identified from repository inspection as duplicated or candidates for cleanup (listed for inventory purposes only; no files are modified or deleted):

1. **Duplicate `.env` files**:
   - `E:\VoiceQueue(gnani.ai)\.env` (root)
   - `E:\VoiceQueue(gnani.ai)\backend\.env` (backend directory)
   *Note: Application startup emits `[Warning] Two .env files detected` and defaults to loading `backend/.env`.*

2. **Duplicate `vercel.json` configurations**:
   - `E:\VoiceQueue(gnani.ai)\vercel.json` (root)
   - `E:\VoiceQueue(gnani.ai)\frontend\vercel.json` (frontend directory)

3. **Duplicate / Overlapping Test Suites**:
   - `E:\VoiceQueue(gnani.ai)\tests\` (root legacy phase test suite with 13 files from Phases D–H)
   - `E:\VoiceQueue(gnani.ai)\backend\tests\` (current active backend test suite with 32 test files)

4. **Duplicate Phase Tracking Files**:
   - `E:\VoiceQueue(gnani.ai)\track_phase` (extensionless marker file)
   - `E:\VoiceQueue(gnani.ai)\track_phase.md` (markdown tracking file)

5. **Unused Default Frontend Boilerplate Assets**:
   - `E:\VoiceQueue(gnani.ai)\frontend\src\assets\react.svg` (default Vite React icon, not referenced in clinic UI)
   - `E:\VoiceQueue(gnani.ai)\frontend\src\assets\vite.svg` (default Vite bundler icon, not referenced in clinic UI)

6. **Redundant Error Catalog Definitions**:
   - `E:\VoiceQueue(gnani.ai)\shared\error_catalog.json` (JSON source)
   - `E:\VoiceQueue(gnani.ai)\frontend\src\errorCatalog.js` (JavaScript dictionary copy)
   - `E:\VoiceQueue(gnani.ai)\backend\app\services\error_catalog.py` (Python dictionary copy)

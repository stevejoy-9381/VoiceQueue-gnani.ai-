# VoiceQueue Progress Tracker

- [x] Phase 0: Project Setup (FastAPI structure, Vite+React, health check, CORS, .env.example, .gitignore, README)
- [x] Phase 1: Gnani Client and Credit Guard (STT/TTS client, global lock, retry on 429, usage logging, credit limit guard, cycling samples, smoke test script)
- [x] Phase 2: Database and Queue Logic (Tokens & VoiceLogs tables, queue service, position math, cancel, call next, REST endpoints, pytest passing)
- [x] Phase 3: Intent Parser, Number Words, Replies (Bilingual NLU, day slot filling, Groq fallback, 0-99 spoken words, templates without digits, 39 pytest tests passing)
- [x] Phase 4: Voice and Text Endpoints, Cached Audio (ffmpeg conversion to 16kHz mono, build_cache script, POST /voice/turn, POST /text/turn, cancel confirmation state, 48 pytest tests passing)
- [x] Phase 5: Mobile Voice UI (Patient Interface: mobile-first '/', large hold-to-talk mic button with pulsing ring, timer, auto-stop 8s, audio replay, token card with 5s polling, language toggle, cancel confirmation Yes/No buttons, typed fallback, Noto Sans fonts, teal #0F766E)
- [x] Phase 6: Clinic Live Queue Dashboard (/clinic route, WebSocket /ws/queue with auto-reconnect, broadcast_queue_change, GET /voice-logs, Today/Tomorrow tabs, Now in consultation card with Mark done / No-show, Waiting list with new-item pulse highlight, live Voice Activity feed, Call next / Seed / Reset actions, 52 pytest tests passing)
- [x] Phase 7: Credits Meter and Safety (GET /usage endpoint, GNANI_CREDITS_PER_CALL optional multiplier, real calls & cached breakdown, Gnani calls badge with amber 80% / red 100% threshold, limit paused banner on both screens, credit limit guard blocking at GNANI_MAX_CALLS=2 with typed fallback, 55 pytest tests passing)
- [x] Phase 8: Testing Tools (docs/test_phrases.csv with 45 benchmark phrases, scripts/run_text_tests.py with 100% accuracy, voice_tests DB model & endpoints, /tests dashboard page with telemetry trial form, noise & language pass rate summary, CSV export, 58 pytest tests passing)
- [x] Phase 9: About Page, README, Deploy (Dedicated /about route with tech stack, model credits, honest limitations, synthetic notice & link to /tests; comprehensive README with ASCII architecture diagram, env vars, cache & test instructions; backend Dockerfile with ffmpeg & docker-compose; Render & Vercel deployment guides; zero secrets in repo; fresh clone runs cleanly)
- [x] Phase 10: Final QA (Strict verification across all 10 checklist items: real mode start, Telugu/English/Mix book-status-cancel, unclear say-again audio, mic denial typed fallback, credit limit pause, double mic tap lock, dashboard actions, 360px & 1366px responsiveness, 0 API keys in dist, clean fresh clone README verification; automated scripts/run_final_qa.py 10/10 PASS)
- [x] Phase 11: Demo Preparation (Added /demo-mode exact recording instructions in README, confirmed 14 pre-cached WAV prompts to preserve credits, implemented hidden Shift+R shortcut to reset & seed 4 demo tokens, added ?clean=1 query mode hiding debug labels on both screens, 10-line recording checklist for 60s video provided)





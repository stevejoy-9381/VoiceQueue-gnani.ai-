# Product Requirements Document (PRD) — VoiceQueue

## 1. Product Name & Summary
- **Product Name**: VoiceQueue
- **Summary**: Voice-first clinic token app for Demo Clinic (`backend/app/main.py#L52`). It enables patients to book, inspect, and cancel outpatient queue tokens using voice in Telugu, English, or Code-mixed (Mix) speech, with real-time queue visibility for clinic staff.

---

## 2. Problem Statement
1. **Clinic Queue Congestion**: Patients arriving at outpatient clinics often wait in crowded physical lines without advance notice of queue position or wait times.
2. **Language & Literacy Barriers**: Traditional self-service kiosks and smartphone applications rely on complex text-heavy menus in English. In South Indian healthcare settings, elderly and vernacular-speaking patients require intuitive, hands-free voice interaction in their primary spoken language (Telugu, Indian English, or bilingual Telugu-English mixing).

---

## 3. Target Users
1. **Patients**:
   - Outpatients seeking clinic tokens for same-day or next-day consultations.
   - Vernacular Telugu speakers, bilingual speakers, and elderly patients requiring high-contrast UI, larger font sizes, and slower speech playback.
2. **Clinic Staff (Receptionists & Nurses)**:
   - Front-desk personnel managing outpatient flow, viewing queue lists, calling the next patient, and resetting or auto-seeding the queue for clinic demonstrations.

---

## 4. User Stories
1. **Patient Booking**: As a patient, I want to speak naturally in Telugu, English, or Mix to request a token for today or tomorrow, so that I receive an assigned token number without standing in a physical line.
2. **Day Clarification**: As a patient, if I do not specify "today" or "tomorrow", I want the assistant to ask "Today or tomorrow?" so that the system never assumes my appointment day.
3. **Queue Status Inquiry**: As a patient with an active token, I want to ask for my token status so that I can hear how many patients are ahead of me and check if my token has been called.
4. **Token Cancellation with Confirmation**: As a patient, I want to cancel my token and be prompted to confirm ("yes" or "no") before the cancellation is finalized so that I do not cancel accidentally.
5. **Staff Queue Management**: As clinic staff, I want a live dashboard showing all waiting and completed tokens with real-time updates so that I can call the next patient with one click.
6. **Accessibility**: As an elderly patient, I want to enable larger text, higher contrast, and slower voice playback (0.85x speed) so that I can easily understand clinic announcements.

---

## 5. Functional Requirements

| Requirement | Description | Status | Evidence in Code |
| :--- | :--- | :--- | :--- |
| **Book Today / Tomorrow** | System books a queue token for today or tomorrow and speaks the assigned number phonetically as words in the reply language. | **IMPLEMENTED** | `backend/app/services/queue_service.py` (`book()`), `backend/app/services/turn_service.py` (`process_turn()`), `backend/app/services/number_words.py` (`to_words()`). |
| **Day Clarification Prompt** | If the patient does not state a day, the system asks "Today or tomorrow?" ("ఈరోజా లేదా రేపా?") without booking or assuming. | **IMPLEMENTED** | `backend/app/services/turn_service.py#L390-L405`, `backend/app/services/replies.py` (`ask_day()`). |
| **Queue Status Inquiry** | Returns active token number, status (`waiting`, `called`, `done`, `cancelled`), and patient count ahead in queue. | **IMPLEMENTED** | `backend/app/services/queue_service.py` (`position()`), `backend/app/services/turn_service.py#L425-L450`, `backend/app/services/replies.py` (`status_reply()`). |
| **Cancel with Confirmation** | Cancellation requests require explicit user confirmation ("Yes" / "No" / "అవును" / "వద్దు") within a 60-second window. | **IMPLEMENTED** | `backend/app/services/turn_service.py` (`_set_pending()`, `_get_pending()`), `backend/app/services/replies.py` (`cancel_prompt()`, `cancel_confirmed()`, `cancel_aborted()`). |
| **Multilingual Support (Telugu, English, Mix)** | System supports Telugu (`te-IN`), English (`en-IN`), and Code-mixed (`mix`) modes; Mix mode determines response language by script and word heuristic. | **IMPLEMENTED** | `backend/app/services/turn_service.py` (`pick_mix_reply_language()`), `backend/app/services/intent.py` (`parse()`), `frontend/src/App.jsx` (`language` state `te`, `en`, `mix`). |
| **Clinic Dashboard Actions** | Front-desk dashboard displays token tables, "Call Next" patient button, and demo reset / reseed controls. | **IMPLEMENTED** | `frontend/src/ClinicDashboard.jsx` (`handleCallNext()`, `handleResetDemo()`), `backend/app/routers/queue_router.py` (`call_next_token()`, `reset_demo()`, `seed_demo_tokens()`). |
| **Voice Activity Feed** | Real-time log displaying patient transcripts, detected intent, token number, and timestamps in IST. | **IMPLEMENTED** | `frontend/src/App.jsx` (Voice Activity Feed table), `backend/app/routers/turn_router.py` (`get_voice_logs()`), `backend/app/services/broadcast.py` (`broadcast_voice_log()`). |
| **Credits & Usage Badge** | UI badge displaying remaining daily Gnani credits and calls used today. | **IMPLEMENTED** | `frontend/src/App.jsx#L1690` (`credits-badge`), `backend/app/routers/turn_router.py` (`get_usage()`), `backend/app/services/credit_protection.py`. |
| **Tests Page** | Developer test interface allowing manual or batch execution of test phrases, acoustic noise labels, and CSV export. | **IMPLEMENTED** | `frontend/src/VoiceTests.jsx`, `backend/app/routers/voice_test_router.py` (`run_single_test()`, `run_full_csv_test()`). |
| **About Page** | Honest informational page detailing named models (Prisma v3.0, Timbre v2.5), dynamic text-only benchmark results, and system limits. | **IMPLEMENTED** | `frontend/src/AboutPage.jsx`, `backend/app/routers/voice_test_router.py` (`get_text_test_summary()`). |
| **Accessibility Toggles** | Elder Mode toggle (high contrast and large font) and Slower Reply toggle (0.85x audio playback with pitch preservation). | **IMPLEMENTED** | `frontend/src/App.jsx#L513-L540` (`slowAudio`, `elderMode`), `frontend/src/App.css` (`.elder-mode`). |

---

## 6. Non-Functional Requirements

| Requirement | Specification | Status | Evidence in Code |
| :--- | :--- | :--- | :--- |
| **Turn Latency** | Pre-synthesized cached replies serve in < 150ms; live turns complete within 3.5s STT/TTS roundtrip. Stage breakdown tracked in milliseconds. | **IMPLEMENTED** | `backend/app/services/latency_tracker.py` (`latency_tracker`), `backend/app/services/monitoring.py` (`StructuredLoggingMiddleware`). |
| **Credit Protection & Limits** | Prevents API credit depletion via per-IP rate limits (default 6 turns / 10 min, 30 / day), per-session caps (10 turns), daily caps, and owner reserve. | **IMPLEMENTED** | `backend/app/services/credit_protection.py` (`can_make_stt_call()`, `can_make_tts_call()`, `is_owner()`). |
| **Synthetic Data Privacy** | All seeded patients use synthetic placeholders (`Demo Patient 1–6`); real names and phone numbers are redacted via regex before logging. | **IMPLEMENTED** | `backend/app/services/queue_service.py#L38-L55` (`auto_seed_if_empty()`), `backend/app/services/privacy.py` (`mask_pii()`). |
| **Timezone Consistency** | All clinic display timestamps formatted in Asia/Kolkata (IST); database persists UTC. | **IMPLEMENTED** | `frontend/src/timeUtils.js` (`formatISTTime()`), `backend/app/services/turn_service.py` (`format_ist_time()`). |
| **Security & Upload Validation** | Audio uploads capped at 10 MB with extension validation; reset endpoints rate-limited in production. | **IMPLEMENTED** | `backend/app/routers/turn_router.py#L60-L75`, `backend/app/routers/queue_router.py#L220-L245`. |

---

## 7. Out of Scope

| Item | Reason | Evidence in Code |
| :--- | :--- | :--- |
| **Real Electronic Health Records (EHR)** | App is designed as a standalone outpatient queue demo; no HL7 / FHIR or hospital database connectors. | Verified: No EHR connectors exist in `backend/app/`. |
| **SMS / WhatsApp Notifications** | Token alerts are handled live via in-app WebSockets; no external telephony gateway configured. | Verified: No Twilio, Gupshup, or SMS gateways in `backend/requirements.txt`. |
| **Multi-Clinic Tenancy** | Single clinic branding and queue per deployment configured via `CLINIC_NAME`. | Verified: `CLINIC_NAME` in `backend/app/config.py#L42`. |
| **Payment Gateway Integration** | Outpatient consultation fees or billing collections are out of scope. | Verified: No payment processing modules in code. |

---

## 8. Success Metrics
1. **Intent Accuracy**: > 90% routing accuracy across conversational Telugu, English, and Code-mixed benchmark phrases (`backend/tests/test_rule_accuracy.py`).
2. **Number Word Parity**: 100% equality between integer token numbers, phonetic number words in voice replies, on-screen patient cards, and the staff dashboard.
3. **Credit Zero-Leakage**: Zero unauthorized Gnani credit consumption on public deployments when demo caps are reached.
4. **Playback Reliability**: 100% audio playback consistency across consecutive turns without browser audio element stalling.

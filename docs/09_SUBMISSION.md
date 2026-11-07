# VoiceQueue — Great Indian AI Internship Challenge 2026 Submission

**Project Title**: VoiceQueue — Voice-First Clinic Token & Queue Management System  
**Developer**: D. Steven Son (Solo Project)  
**Target Organization**: Demo Clinic (Rural & Tier-2/3 Andhra Pradesh & Telangana Outpatient Clinics)  
**Code Repository**: [`https://github.com/stevejoy-9381/VoiceQueue-gnani.ai-`](https://github.com/stevejoy-9381/VoiceQueue-gnani.ai-)  

---

## 1. 200-Word Plain-Language Summary

VoiceQueue is a voice-first token booking and queue management system designed for small outpatient clinics in India. In many community clinics, patients wait for hours in crowded waiting rooms because they cannot read digital portal forms or navigate complex smartphone apps. VoiceQueue eliminates this barrier by allowing patients to speak naturally in Telugu, English, or a mix of both to book an appointment, check their live position in line, or cancel a token.

When a patient speaks, VoiceQueue converts their speech into text using Gnani Prisma (`prisma-v3.0`), resolves their intent using a hardened rule engine, updates the clinic queue database in real time, and responds with natural spoken audio synthesized via Gnani Timbre (`timbre-v2.5`). Token numbers are spelled out as full words so audio sounds clear and natural. For elderly patients, VoiceQueue includes a high-contrast mode with 30% larger text and a toggle that slows spoken replies down to 85% speed. Receptionists manage the line from a live dashboard with keyboard shortcuts and instant WebSocket updates. VoiceQueue proves that vernacular voice interfaces can make everyday healthcare accessible to everyone, regardless of digital literacy.

*(Word count: 182 words)*

---

## 2. Problem Statement & Target Users

### 2.1 The Problem
* **Clinic Congestion**: Primary healthcare clinics in Andhra Pradesh and Telangana face crowded waiting areas where walk-in patients wait hours without knowing when they will be seen.
* **The Digital Divide**: Existing hospital management portals and mobile apps require reading English, selecting dates from calendars, and filling out multi-step forms. For elderly or semi-literate patients, these apps are unusable.
* **Language Barriers**: Most voice interfaces assume standard English or Hindi. Native Telugu speakers and patients speaking colloquial mixed sentences ("*naaku repu token kavali*", "*what is my token status?*") are excluded.

### 2.2 Target Users
1. **Clinic Patients**:
   * Native Telugu speakers, elderly individuals, and semi-literate patients who prefer speaking over typing.
   * Patients with basic smartphones using mobile browsers.
2. **Clinic Reception Staff & Doctors**:
   * Busy receptionists who need to advance queues quickly, call patients into consultation rooms, handle cancellations, and monitor waiting room capacity without manual paper tokens.

---

## 3. Gnani AI Models & Integration Architecture

VoiceQueue integrates state-of-the-art speech models provided by Gnani AI:

### 3.1 Speech-to-Text (STT)
* **Model**: **Prisma (`prisma-v3.0`)**
* **Supported Languages in Code**: `te-IN` (Telugu) and `en-IN` (English).
* **Audio Input Format**: 16,000 Hz, 16-bit, single-channel (mono) PCM WAV.
* **Code Implementation**: [`backend/app/services/gnani.py:stt()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L90-L150)

### 3.2 Text-to-Speech (TTS)
* **Model**: **Timbre (`timbre-v2.5`)**
* **Voices Used**:
  * Telugu (`te-IN`): **`Lavanya`** (verified female voice for Telugu).
  * English (`en-IN`): **`Trupti`** (verified female voice for Indian English).
* **Audio Output Format**: 16 kHz 16-bit mono WAV.
* **Code Implementation**: [`backend/app/services/gnani.py:tts()`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L160-L245)

### 3.3 Concurrency Control
* **Lock**: `_concurrency_lock` in [`backend/app/services/gnani.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/gnani.py#L28-L35).
* Strictly enforces **one request at a time** across all client turns, preventing concurrent calls that could overload API quotas or cause connection timeouts.

---

## 4. What is Rule-Based vs Gnani AI

| Responsibility | Engine / Technology | Rationale & Code Evidence |
| :--- | :--- | :--- |
| **Speech Recognition** | **Gnani Prisma (`prisma-v3.0`)** | Translates spoken audio waveform into text transcripts across Telugu, English, and Mix. |
| **Voice Synthesis** | **Gnani Timbre (`timbre-v2.5`)** | Converts clinic reply text and dynamic token sentences into natural spoken audio. |
| **Intent Parsing** | **Deterministic Rule Engine** | **Gnani provides no conversational chat model / LLM**. All intent routing (`BOOK`, `STATUS`, `CANCEL`, `YES`, `NO`) is handled by deterministic regex, fuzzy matching, and keyword rules in [`backend/app/services/intent.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/intent.py). |
| **Day Resolution** | **Rule-Based Engine** | Automatically resolves `today` vs `tomorrow` from colloquial markers (`repu`, `ee roju`, `morning`, `tomorrow`, `today`). |
| **Phonetic Number Words** | **Rule-Based Dictionary** | Converts numbers into full spelled Telugu words (`ఒకటి`, `రెండు`, `మూడు`) in [`backend/app/services/replies.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/replies.py) so TTS sounds natural. |
| **Queue State Mutation** | **SQLAlchemy ORM** | Handles database state changes (waiting -> in_consult -> done/no_show). |
| **Optional NLU Fallback** | **Groq Llama-3.1-8B-Instant** | Used *only* as a fallback if the rule engine cannot resolve intent and `GROQ_API_KEY` is configured. |

---

## 5. Developer Contribution

* **Team Structure**: Built **100% solo** by **D. Steven Son**.
* **Scope of Work**:
  * Designed and implemented the complete FastAPI backend architecture, SQLAlchemy database models, and WebSocket broadcasting manager.
  * Authored the multi-stage audio processing pipeline: FFmpeg conversion, acoustic cleaning (150Hz–3800Hz bandpass and noise gate), quality gates, and WAV byte repair.
  * Developed the deterministic bilingual intent parser with 100% accuracy across 60 benchmark sentences.
  * Built the mobile-first React frontend with warm coffee & beige aesthetic, elder accessibility mode, 0.85x slower speech audio toggle, and local 3s mic diagnostic.
  * Designed the live receptionist dashboard with summary KPIs and keyboard shortcuts (`N` for Call next, `D` for Mark done).
  * Implemented credit protection architecture with IP throttling, session caps, reserve buffer, and pre-rendered WAV cache.
  * Wrote 31 backend test suites, 3 frontend unit test files, and Playwright E2E browser automation specs.

---

## 6. Honest Limitations

1. **Single-Clinic Scope**: VoiceQueue is scoped strictly to outpatient queues for a single clinic location (Demo Clinic). Multi-facility and hospital-wide department transfers are out of scope.
2. **Turn-Based Half-Duplex Audio**: Communication is half-duplex (hold-to-talk / tap-to-talk). Full-duplex conversational interruption (barge-in while the assistant is speaking) is not supported.
3. **Deterministic Intent Engine**: Because Gnani does not offer a generative conversational LLM, complex clinical medical diagnosis questions are intentionally rejected; the system strictly handles queue scheduling (`BOOK`, `STATUS`, `CANCEL`).
4. **No Real SMS / WhatsApp Delivery**: Token confirmation numbers are displayed on-screen and spoken aloud. Twilio/SMS gateway integration is omitted to protect user privacy.
5. **Acoustic Noise Matrix Status**: While text-based rules pass at 100% (45/45 and 60/60) and 128 general live test turns were recorded, empirical trials across the 3x3 background noise grid (quiet, fan, street) are documented honestly as **NOT MEASURED**.

---

## 7. Synthetic Data & Privacy Statement

> [!IMPORTANT]
> **Zero Protected Health Information (PHI) Stored**:  
> All patient tokens, appointment dates, and consultation records in VoiceQueue are **100% synthetic**.  
> The system does not collect, request, or store real patient names, government Aadhaar numbers, or phone numbers. All interaction logs are scrubbed via automated regex masking in [`backend/app/services/privacy.py`](file:///e:/VoiceQueue(gnani.ai)/backend/app/services/privacy.py).

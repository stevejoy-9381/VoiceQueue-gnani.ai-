# VoiceQueue (`gnani.ai`)

> **Voice-First Clinic Token & Queue Management System for Demo Clinic**  
> *Built for the Great Indian AI Internship Challenge 2026 by D. Steven Son (Solo Developer)*

---

## Overview

VoiceQueue allows clinic patients in Andhra Pradesh and Telangana to book, check, and cancel outpatient appointments simply by speaking in **Telugu**, **English**, or **Mix (Telugu + English)**.

The system pairs **Gnani AI** speech technology with a responsive React frontend and a FastAPI backend to eliminate waiting room congestion and bridge the digital literacy divide.

---

## Key Features

- **Voice-First Interaction**: Hold SPACE (desktop) or tap microphone (mobile) to book tokens, query queue status, or cancel appointments.
- **Gnani Speech Integration**:
  - **Speech-to-Text (STT)**: Gnani Prisma (`prisma-v3.0`) for Telugu (`te-IN`) and English (`en-IN`).
  - **Text-to-Speech (TTS)**: Gnani Timbre (`timbre-v2.5`) with native voices `Lavanya` (Telugu) and `Trupti` (English).
- **Phonetic Spelled Words**: Numbers are converted into full Telugu words (`ఒకటి`, `రెండు`, `మూడు`) for natural pronunciation.
- **Elder-Friendly Accessibility**: High-contrast mode with 30% larger text and a toggle that slows spoken replies to 85% speed.
- **Live Receptionist Dashboard**: Real-time patient management via WebSockets with keyboard shortcuts (`N` for Call next, `D` for Mark done).
- **Acoustic Cleaning & Quality Gates**: 150Hz–3800Hz bandpass filtering and automatic rejection of silence or corrupted audio.
- **Credit Protection**: Multi-tier rate limiting and pre-rendered WAV caching to protect API quotas.

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ or 20+
- FFmpeg installed and available on `PATH`

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/stevejoy-9381/VoiceQueue-gnani.ai-.git
cd VoiceQueue-gnani.ai-

# Set up virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and supply your GNANI_API_KEY

# Start backend server
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
# In a new terminal:
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## Available Routes

- `/`: Patient Voice Application
- `/clinic`: Real-time Receptionist Dashboard
- `/tests`: Voice Testing & Accuracy Telemetry
- `/about`: System Overview, Models, and Disclosure

---

## Running Tests

```bash
# Backend pytest suite
pytest backend/tests/ -v

# Frontend unit tests
cd frontend && npm test

# Playwright E2E browser tests
cd frontend && npx playwright test
```

---

## System Limitations & Honest Disclosures

1. **Single Clinic Scope**: Built specifically for outpatient token scheduling at Demo Clinic.
2. **Deterministic Intent**: Gnani AI provides STT/TTS without a conversational LLM; all intent routing (`BOOK`, `STATUS`, `CANCEL`) uses deterministic rule parsing.
3. **Turn-Based Half-Duplex**: Patients speak, release, and listen; continuous full-duplex barge-in is not supported.
4. **Synthetic Data Only**: All patient records and tokens are simulated. Zero protected health information (PHI) or real phone numbers are collected or stored.

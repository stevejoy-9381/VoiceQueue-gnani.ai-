# VoiceQueue UI/UX Design & Component Specification

**Document**: `06_UI_UX.md`  
**Application**: VoiceQueue (`gnani.ai`)  
**Design Theme**: Warm Coffee & Beige Medical Clinic Palette  
**Audience**: Outpatient clinic patients (with elder accessibility) and clinic reception staff  

---

## 1. Design System & Colour Tokens

All colour tokens are defined in [`frontend/src/index.css`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/index.css) and aliased across [`frontend/src/App.css`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.css), [`frontend/src/ClinicDashboard.css`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/ClinicDashboard.css), [`frontend/src/VoiceTests.css`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/VoiceTests.css), and [`frontend/src/AboutPage.css`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.css).

### 1.1 Coffee Brown and Beige Tokens

| Token Variable | Hex Code | Role & Usage |
| :--- | :--- | :--- |
| `--coffee-900` | `#3B2418` | Primary dark headings, prominent cards, dark buttons, code blocks, borders, footer links |
| `--coffee-600` | `#6F4E37` | Primary interactive buttons, links, active tab fills, success accents |
| `--coffee-300` | `#A67B5B` | Interactive hover states, pulse rings, focus ring outlines |
| `--beige-100` | `#F5EBDD` | Global page background canvas |
| `--beige-50` | `#FBF6EE` | Card backgrounds, top navigation bars, input fields, light surface areas |
| `--beige-300` | `#E3D5C0` | Surface borders, divider lines, disabled boundaries |
| `--accent` | `#C8893B` | Small highlights only (warning pills, tags, chips, badges, icons) |
| `--text` | `#3B2418` | Standard body typography on light backgrounds |
| `--text-on-dark`| `#FBF6EE` | High-contrast typography on coffee-colored buttons and headers |
| `--text-muted` | `#5C3D2E` | Secondary captions, timestamps, instructions |
| `--danger-red` | `#9E2A2B` | Alert banners, error messages, cancel action buttons |
| `--danger-light`| `#FDF2F0` | Error card backgrounds, warning banner fills |

### 1.2 High-Contrast Elder Mode Tokens
When the elder-friendly accessibility toggle is enabled, the palette shifts to maximum contrast:
* High-contrast text & outlines: `#1A0F0A`
* Card surface: `#FFFDF8`
* Canvas background: `#F7EFE3`
* Muted text: `#2B170E`

### 1.3 Typography Stack
```css
font-family: "Noto Sans Telugu", "Noto Sans Devanagari", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```
Ensures complete Unicode rendering of Telugu ligatures and English text across mobile devices.

---

## 2. Page Specifications

### 2.1 Patient Voice View (`/`)
Mobile-first conversational screen for booking, checking status, and cancelling clinic tokens. Handled in [`frontend/src/App.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/App.jsx).

```
+-------------------------------------------------------+
|  Demo Clinic                 [ Dashboard -> ]         |
|  Clinic tagline in selected language                  |
|  [ తెలుగు ]   [ English ]   [ Mix ]                   |
+-------------------------------------------------------+
|  [x] Large text & contrast    [ ] Slower reply        |
+-------------------------------------------------------+
|  Try saying: ["repu token kavali"] ["token status"]   |
|  > How it works (Collapsible 1-2-3 steps)             |
+-------------------------------------------------------+
|                                                       |
|                     ((  MICROPHONE  ))                |
|                       120px Button                    |
|                                                       |
|  "Hold SPACE to speak. Earphones work best."          |
|  "On a phone, tap once to start, tap again to stop"   |
|  Mic: Default | [Test Sound] | [Mic Check]            |
+-------------------------------------------------------+
|  YOU SAID:                                            |
|  "repu naaku token kavali"                            |
+-------------------------------------------------------+
|  CLINIC REPLY:                       [🔊 Say again]   |
|  "మీ టోకెన్ నంబర్ 1. రేపటి కోసం బుక్ చేసాము."         |
|  EN: "Your token number is 1. Booked for tomorrow."   |
+-------------------------------------------------------+
|  BOOKED TOKEN:                                        |
|  TOMORROW                             [ WAITING ]     |
|  TOKEN #1                                             |
|  Ahead in queue: 0 patients                           |
+-------------------------------------------------------+
|  [ v Type instead of speaking ]                       |
|  [ Input box...                         ] [ Send ]    |
+-------------------------------------------------------+
|  About VoiceQueue & Limitations ->                    |
+-------------------------------------------------------+
```

#### Components
1. **Header & Navigation Bar**: Clinic title, localized tagline, link to `/clinic` dashboard.
2. **Language Selector**: 3 mutually-exclusive buttons (`తెలుగు`, `English`, `Mix`).
3. **Accessibility Bar**: Checkboxes for Large Text / Elder Contrast and Slower Audio Reply.
4. **Try Saying Chips**: Pre-populated one-tap example query buttons.
5. **How It Works Accordion**: Collapsible 3-step explanation of the voice queue process.
6. **Microphone Interaction Zone**:
   * Circular microphone button (120px standard, 156px elder mode).
   * Live audio volume meter bar during speech capture.
   * Device dropdown selector & active microphone label.
   * "Test Sound" speaker diagnostic button.
   * "Mic Check" 3-second local acoustic diagnostic tool.
7. **"You Said" Card**: Displays STT recognized transcript.
8. **"Clinic Reply" Card**:
   * Assistant reply text.
   * Dual replay controls: "🔊 Replay" and "🔊 Say that again".
   * Inline English translation for Telugu replies.
   * Autoplay unblock button ("🔊 Tap to hear the reply") if browser blocks autoplay.
9. **Patient Token Card**:
   * Token day badge (`TODAY` or `TOMORROW`).
   * Large token number (e.g., `#4`).
   * Queue position counter (`Ahead in queue: X patients`).
   * Status badge (`WAITING`, `IN_CONSULT`, `DONE`, `CANCELLED`).
10. **Typed Fallback Accordion**: Text input field and Send button for silent or noisy environments.
11. **Token Called Alert Banner**: Full-width pulsing green banner when receptionist calls patient into consultation room.

#### View States
* **Idle State**: Microphone button steady coffee brown (`#6F4E37`). Placeholder text in transcript and reply cards.
* **Recording State**: Microphone button pulses with coffee glow ring. Status reads `Listening...`. Live volume meter animates with input audio energy.
* **Processing State**: Microphone disabled. Status reads `Understanding...`.
* **Speaking / Playing State**: Status reads `Speaking reply...`. Audio plays through Web Audio element.
* **Empty State**: When no token is held, displays dashed card: `No token yet. Try saying: I need a token for tomorrow`.
* **Error State**: Displays red alert card with friendly bilingual message and localized action button (e.g. `Try again`, `Allow microphone`, `Use typing below`).
* **Confirmation State**: When patient asks to cancel, displays confirmation banner with `Yes` and `No` buttons.

---

### 2.2 Clinic Staff Dashboard (`/clinic`)
Real-time operations center for receptionists and doctors. Handled in [`frontend/src/ClinicDashboard.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/ClinicDashboard.jsx).

#### Components
1. **Dashboard Header**: Clinic title, Day tab selector (`Today` / `Tomorrow`), WebSocket connection status dot (`Live` / `Reconnecting`), Last updated timestamp.
2. **Credits & Usage Meter**: Real-time counter of Gnani STT/TTS calls against daily cap (`Calls: X/150`, `Reserve: 40`), estimated credits used.
3. **Summary KPI Counter Cards**:
   * `Waiting` (count of patients waiting)
   * `In Consultation` (active patient)
   * `Done Today` (completed visits)
   * `Cancelled` (cancelled tokens)
4. **Action Control Bar**:
   * `📢 Call Next Patient` (keyboard shortcut: `N`)
   * `🌱 Seed Demo Data`
   * `🔄 Reset Demo`
5. **Left Column — Now in Consultation**:
   * Giant token badge (`#1`)
   * Patient language preference
   * `✓ Mark Done (D)` button
   * `✕ No-Show` button
6. **Left Column — Waiting Patient Queue**:
   * Ordered list of waiting patients with queue position, token number, and language badge.
   * Row flashes with animated highlight pulse when a new voice booking arrives.
7. **Right Column — Voice Activity Feed**:
   * Live streaming audit feed of patient voice turns.
   * Timestamp in IST, intent badge (`BOOK`, `STATUS`, `CANCEL`), recognized transcript, token number, error badges.
   * `Clear voice log` maintenance button.

#### View States
* **Loading State**: Displays skeleton / loading indicator while initial queue data is fetched.
* **Empty Queue State**: Shows `No patient currently in consultation` with a prompt to click `Call Next Patient`. Waiting list shows `No patients waiting`.
* **Error / Disconnected State**: Live dot turns orange (`Reconnecting`) with automated exponential backoff reconnection.

---

### 2.3 Voice Testing & Telemetry Page (`/tests`)
Acoustic testing harness for logging and verifying accuracy across noise conditions. Handled in [`frontend/src/VoiceTests.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/VoiceTests.jsx).

#### Components
1. **Header & Navigation**: Title, subtitle, `Export CSV` download button, `← Back to Dashboard` link.
2. **Trial Logging Form (Left Column)**:
   * Language selector: `Telugu (తెలుగు)`, `English`, `Mix (Telugu + English)`
   * Noise environment: `Quiet Room`, `Fan / AC Noise`, `Street / Traffic Noise`
   * Expected Intent dropdown (`BOOK`, `STATUS`, `CANCEL`, `YES`, `NO`, `UNKNOWN`)
   * Got Intent dropdown
   * "Sentence I meant to say" text field
   * "Recognized Transcript" textarea
   * Trial Outcome toggle buttons: `✓ PASS` / `✕ FAIL`
   * Notes / observations field
   * `Save Voice Test Row` submit button
3. **3x3 Language x Noise Grid Summary Card (Right Column)**:
   * Matrix comparing pass rates across 3 languages and 3 noise environments.
   * Color-coded pass rate pills:
     * Green: `>= 90%`
     * Amber: `70% - 89%`
     * Red: `< 70%`
   * Overall system accuracy badge.
4. **Historical Trial Records Table (Bottom Full-Width)**:
   * Tabular list of every trial with ID, PASS/FAIL badge, language, noise level, expected intent, got intent, intended sentence, recognized transcript, notes, and IST timestamp.

---

### 2.4 About Page (`/about`)
Documentation and disclosure page. Handled in [`frontend/src/AboutPage.jsx`](file:///e:/VoiceQueue(gnani.ai)/frontend/src/AboutPage.jsx).

#### Components
1. **Header**: "About VoiceQueue" title, tagline, "✓ Reviewed by a native speaker" verification badge, navigation pills to Patient App, Clinic Dashboard, and Test Telemetry.
2. **Synthetic Data Disclosure Banner**: Clear notice that all patient data, tokens, and records are simulated.
3. **"What is VoiceQueue?" Card**: Problem statement and architecture overview.
4. **"Models & Speech Stack" Card**:
   * STT: Gnani Prisma (`prisma-v3.0`)
   * TTS: Gnani Timbre (`timbre-v2.5` using `Lavanya` for Telugu and `Trupti` for English)
   * NLU Fallback: Groq (`Llama-3.1-8B-Instant`, shown only if configured)
5. **"System Limits & Scope" Card**: Synthetic data notice, deterministic intent routing rationale, single-clinic outpatient scope, privacy guarantees (no phone numbers stored).
6. **"Test Results" Card**:
   * Text-only intent test score badge (e.g. `45 of 45 passed (no audio)`).
   * Live 3x3 empirical voice testing matrix.
   * Shortcut button to open `/tests`.
7. **Footer**: Challenge attribution and GitHub repository hyperlink.

---

## 3. Accessibility & Elder-Friendly Features

### 3.1 Large Text & High Contrast Mode (`.elder-mode`)
* **Text Sizing**: Base typography increases by ~30% (from 18px to 23px; headers to 28px).
* **Button Heights**: Interactive targets (mic, replay, confirm, type inputs) expand to at least 64px tall (`min-height: 64px`).
* **Visual Contrast**: Background switches to warm cream (`#FFFDF8` on `#F7EFE3`), text and borders switch to maximum darkness (`#1A0F0A`), eliminating light brown gradients.
* **Large Microphone Target**: Microphone wrapper expands to 170x170px; inner button expands to 156x156px with 4px dark border.
* **Focus Outlines**: Unambiguous 3px solid `#3B2418` focus rings with 2px offset on all keyboard focusable controls (`:focus-visible`).

### 3.2 Slower Audio Reply Toggle
* **Implementation**: Controlled via checkbox in accessibility bar (`slowAudio` state in `App.jsx`).
* **Playback Rate**: Sets `HTMLAudioElement.playbackRate = 0.85` (15% reduction in speech tempo).
* **Benefit**: Allows elderly patients or non-native speakers to comfortably comprehend spoken token numbers and consultation instructions without pitch distortion.

### 3.3 Built-in 3-Second Microphone Diagnostic ("Mic Check")
* **Operation**: Click `🎙️ Mic check` in the patient UI.
* **Zero Gnani Calls**: Captures audio locally for 3 seconds via Web Audio API without calling backend STT models.
* **Real-time Computation**: Calculates RMS volume energy and Peak amplitude.
* **Automated Diagnosis**:
  * `Good` (RMS > 0.04, Peak < 0.95): "Microphone level is clear and ready to use."
  * `Too quiet` (RMS <= 0.04): "I can hardly hear you. Speak louder or move the mic closer (15-20 cm)."
  * `Too loud` (Peak >= 0.95): "Microphone input is clipping. Lower your input volume or move slightly away."
  * `Too noisy`: "High background noise detected. Use earphones or move to a quieter room."

---

## 4. Mobile Responsiveness & Touch Interactions

### 4.1 Mobile-First Viewport
* The patient view is constrained to a comfortable mobile viewport (`max-width: 480px` centered on desktop displays) ensuring consistency between mobile phones and kiosk tablets.
* At compact screens (`max-width: 380px`), padding shrinks to `12px 8px 30px` and language pills scale down so no horizontal scrollbars occur.

### 4.2 Tap-to-Talk vs Spacebar Hold
* **Desktop Interaction**: Hold `SPACE` bar to speak; release `SPACE` to send.
* **Mobile Interaction**: On touchscreen phones, tapping the large circular microphone button once starts recording (showing a pulsing ring and audio volume meter); tapping it a second time stops recording and sends the turn.

### 4.3 Autoplay Restriction Handling
Mobile browsers frequently block audio autoplay until the user explicitly interacts with the DOM:
1. **First-Visit Banner**: Encourages users to tap the screen once upon arrival to initialize audio permissions.
2. **"Tap to Hear" Fallback Button**: If an audio response play promise is rejected with `NotAllowedError`, a visible button appears: `🔊 Tap to hear the reply`. Tapping it plays the response immediately within a verified user gesture context.

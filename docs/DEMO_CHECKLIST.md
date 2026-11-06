# Demo Recording Checklist & Script (Phase P2-9)

Follow this checklist before recording the video demonstration to ensure a smooth, professional, and reproducible presentation.

---

## 1. Pre-Recording Preparation

### Step 1: Clean Reset and Seed
- Reset the demonstration state using one of two methods:
  1. Terminal: Run `python scripts/demo_reset.py`
  2. Dashboard: Press **`Shift + R`** on the Clinic Dashboard keyboard and confirm the dialog.
- This creates **4 synthetic demo tokens** (Token #1 `in-consultation`, Tokens #2–4 `waiting`).

### Step 2: Synthetic Data & Privacy Guard
- **Strictly synthetic**: Never utter real names, real Indian mobile numbers, or personal identifying information.
- Speak generic names or let the system assign automatic demo tokens (`Token #5`).

### Step 3: Acoustic Environment
- Record in a quiet indoor room.
- Turn off ceiling fans, air conditioners, and close exterior doors/windows to minimize background noise.

### Step 4: Earphones with Microphone
- Use a dedicated headset or wired earphones with an inline microphone.
- Position the mic 15–20 cm from your mouth.
- Using earphones prevents speaker feedback into the microphone during audio playback.

### Step 5: Sound & Mic Check
- In non-clean mode (`/?dev=1`), run the built-in **Mic check** (records 3 seconds, evaluates RMS and peak).
- Verify the verdict is **Good** (not *Too quiet*, *Too loud*, or *Too noisy*).
- Tap the **Test sound** button to verify browser audio output permissions.

### Step 6: Production Key & Meter Verification
- Ensure `GNANI_API_KEY` is loaded and the daily calls meter has sufficient quota (`/usage`).
- Set `OWNER_KEY` if testing or demonstrating credit threshold controls.

### Step 7: Screen & Tab Layout
- Use a side-by-side 2-window split screen:
  - **Left Window (Mobile Viewport ~360px–390px)**:  
    `http://localhost:5173/?clean=1`  
    *(The `?clean=1` flag hides developer pills, mic device selector details, and technical logs).*
  - **Right Window (Desktop Viewport ~1366px or 1920px)**:  
    `http://localhost:5173/clinic?clean=1`  
    *(Shows live WebSocket changes, consultation card, ordered waiting queue, and voice feed).*

---

## 2. The Three Demonstration Sentences

Record these three exact sentences in sequence to showcase the full voice lifecycle:

### Sentence 1: Booking a Token (Telugu / Mix)
- **What to say**:  
  *"రేపు నాకు టోకెన్ కావాలి"* (`repu naaku token kavali`)  
  *or in Mix mode*: *"repu doctor appointment book cheyyandi"*
- **Action**: Hold the microphone button (or press and hold SPACE), speak clearly, then release.
- **Expected Outcome**:
  1. Status updates: *Listening* -> *Understanding...* -> *Speaking reply*.
  2. Spoken reply synthesized with number as spoken words (*"ఐదు"*, never digit 5).
  3. Patient Token Card appears on the phone screen with Token #5 for Tomorrow.
  4. Clinic Dashboard updates in real time over WebSocket: Token #5 appears in the waiting list within 1 second.

### Sentence 2: Queue Status & Position Check (English / Mix)
- **What to say**:  
  *"What is my token status?"*  
  *or in Mix mode*: *"my token status cheppandi"*
- **Action**: Hold the microphone button, speak, and release.
- **Expected Outcome**:
  1. System checks the active token from the current session.
  2. Replies with exact queue position (*"There are 3 patients ahead of you in line"*).
  3. Position counter updates live on the phone card.
  4. On the dashboard, press **N** (or click **Call Next Patient**): Token #2 moves into consultation, and the phone's ahead count drops automatically without reloading.

### Sentence 3: Cancellation Flow with Confirmation (Telugu / English)
- **What to say**:  
  *"నా టోకెన్ క్యాన్సల్ చేయండి"* (`naa token cancel cheyyandi`)  
  *or in English*: *"Cancel my token"*
- **Action**: Hold the microphone button, speak, and release.
- **Expected Outcome**:
  1. System initiates 60-second confirmation window:  
     *"Are you sure you want to cancel your token?"*
  2. Two large, elder-friendly 64px confirmation buttons appear: **Yes, cancel** and **No, keep**.
  3. Tap **Yes, cancel** (or say *"avunu"* / *"yes"*).
  4. Spoken confirmation confirms cancellation. Token status on dashboard immediately updates to *Cancelled*.


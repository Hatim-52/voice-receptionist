# Voice AI Doctor Appointment Assistant

A complete, production-grade voice-based doctor appointment system. A caller speaks to an AI receptionist directly in their browser using natural voice. The agent checks doctor schedules, books appointments, and cancels appointments in real time. A modern healthcare dashboard displays live doctor schedules, real-time appointments with animated change highlights, a phone-style call interface, a live audio waveform, and synthesized Web Audio tones.

---

## Architecture

```
[Browser Mic] 
      │ (WebRTC Audio Stream)
      ▼
[Pipecat SmallWebRTC Transport]
      │
      ▼
[Silero VAD] (Local Voice Activity Detection)
      │
      ▼
[ElevenLabs Realtime STT] (Speech-to-Text via Scribe)
      │
      ▼
[Google Gemini 2.5 Flash] (Function Calling LLM) ──► [SQLite DB & Tools]
      │                                                │
      ▼                                                ▼
[ElevenLabs TTS] (Turbo v2.5 Voice Synthesis)    [FastAPI Live Events (SSE)]
      │                                                │
      ▼ (WebRTC Audio Out)                             ▼ (Real-time Sync)
[Browser Speaker / Headphones]                   [React + TypeScript Dashboard]
```

- **Voice Pipeline Framework:** [Pipecat](https://github.com/pipecat-ai/pipecat) (Python 3)
- **STT & TTS:** ElevenLabs (Realtime STT + Eleven Turbo v2.5 TTS)
- **LLM:** Google Gemini 2.5 Flash via Pipecat Google Service (Free Quota Tier)
- **Voice Activity Detection (VAD):** Silero VAD (integrated into pipeline)
- **Transport:** SmallWebRTC transport (`@pipecat-ai/small-webrtc-transport` & `SmallWebRTCTransport`)
- **Backend Server:** FastAPI with WebRTC signaling, REST API, and Server-Sent Events (SSE)
- **Frontend Dashboard:** React 19 + Vite + TypeScript + Tailwind CSS

---

## Core Rules & Guardrails

1. **Caller Identification:** Callers have no logins, passwords, or OTPs. They are identified **strictly by the 10-digit phone number they speak aloud**.
2. **Mandatory Digit-by-Digit Verification:** Before booking or cancelling, the agent **must** read the phone number back digit by digit (e.g. *"Just to confirm, is your number 9 8 7 6 5 4 3 2 1 0?"*) and receive an explicit verbal "yes" from the caller.
3. **Spoken Number Normalization:** Spoken words (*"nine eight double seven..."*, *"zero"*, *"oh"*, etc.) are normalized and validated into standard 10-digit format in `tools.py`.
4. **Collision Prevention:** SQLite enforces double-booking prevention at the database level with a unique partial index:
   ```sql
   CREATE UNIQUE INDEX idx_active_appointment ON appointments (doctor_id, date, time) WHERE status = 'confirmed';
   ```
5. **Natural Voice Persona:** Short responses (1–2 sentences per turn), offering at most 2–3 slots at a time to prevent audio cognitive overload.

---

## Directory Structure

```
├── backend/
│   ├── bot.py             # Pipecat voice pipeline, VAD, STT, Gemini LLM, TTS, tools
│   ├── tools.py           # Availability, booking, cancellation & phone normalizer
│   ├── db.py              # SQLite schema, doctors seeding, slot queries
│   ├── server.py          # FastAPI server: WebRTC offer, REST API, live SSE stream
│   ├── test_tools.py      # Automated tests for tools and database logic
│   ├── requirements.txt   # Backend dependencies
│   └── .env.example       # Example environment variables
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx             # Clinic brand, live status pill, reset & call buttons
│   │   │   ├── DoctorsList.tsx        # 6 specialists with 7-day interactive slot schedules
│   │   │   ├── AppointmentsTable.tsx  # Live table with animated update highlights
│   │   │   └── PhoneCallModal.tsx     # Phone UI, timer, waveform, live transcript, controls
│   │   ├── services/
│   │   │   ├── audioSounds.ts         # Web Audio API ringtone and disconnect beeps
│   │   │   ├── voiceClient.ts         # WebRTC client & audio frequency analyzer
│   │   │   └── sseEvents.ts           # SSE & WebSocket live event consumer
│   │   ├── types.ts                   # TypeScript interfaces
│   │   ├── App.tsx                    # Main dashboard application
│   │   ├── main.tsx                   # React root entry
│   │   └── index.css                  # Tailwind styles & animations
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── PIPELINE.md            # Plain-language pipeline explanation for submission
├── DEMO_SCRIPT.md         # 2-minute video walkthrough script
├── .env.example           # Root environment variable template
├── .gitignore
└── README.md
```

---

## Setup & Running

### 1. Prerequisites
- **Python:** 3.10+ (tested and verified on Python 3.13)
- **Node.js:** 18+ (tested on Node v24)
- **API Keys:**
  - Google Gemini API Key (free quota from [Google AI Studio](https://aistudio.google.com))
  - ElevenLabs API Key (from [ElevenLabs](https://elevenlabs.io))

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env` in the project root or inside `backend/`:

```bash
# On Linux/macOS:
cp .env.example backend/.env

# On Windows (PowerShell):
Copy-Item .env.example backend\.env
```

Open `backend/.env` and insert your actual API keys:
```env
ELEVENLABS_API_KEY=your_actual_elevenlabs_api_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
GOOGLE_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Install & Start Backend

```bash
# Navigate to backend and install dependencies
pip install -r backend/requirements.txt

# Run the unit tests to verify database and tools without voice/network:
python -m backend.test_tools

# Start the FastAPI server:
python -m uvicorn backend.server:app --port 8000 --reload
```
The backend starts at `http://localhost:8000`.

### 4. Install & Start Frontend

Open a new terminal window:
```bash
# Navigate to frontend and install dependencies
cd frontend
npm install

# Start the Vite development server:
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Manual Testing Checklist

Follow this checklist to test the full system with your microphone:

- [ ] **Initial Page Load:** Verify that all 6 doctors are listed with their room numbers and available slots.
- [ ] **Date Tabs:** Click "Tomorrow" or another day in the doctor list to view date-specific slots.
- [ ] **Try Call Action:** Click **"Try Call"** in the top header.
  - [ ] Browser requests microphone permission (click **Allow**).
  - [ ] The phone-style modal appears with status "Calling clinic...".
  - [ ] Telephony ringing tone plays through your speakers.
- [ ] **Call Connected:**
  - [ ] State transitions to **Connected** with timer counting up (`00:01`, `00:02`...).
  - [ ] Receptionist greets you: *"Hello! Thank you for calling Apollo Clinic. I can help you check doctor availability, book an appointment, or cancel an appointment. How can I help you today?"*
  - [ ] Live transcript appears inside the phone screen.
  - [ ] Waveform bars react to voice audio.
- [ ] **Ask for Availability:** Say *"Check Dr. Priya Sharma's available slots for tomorrow."*
  - [ ] Agent replies offering 2–3 slots (e.g. 10:30 AM, 11:30 AM, 2:00 PM).
- [ ] **Book a Slot:** Say *"I would like to book 10:30 AM."*
  - [ ] Agent asks for your phone number.
  - [ ] Say your 10-digit number (e.g. *"Nine eight seven six five four three two one zero"*).
  - [ ] **Protocol Check:** Agent reads the number back digit by digit and asks for confirmation.
  - [ ] Say *"Yes, that is correct."*
- [ ] **Live Dashboard Sync:**
  - [ ] The booking confirmation card pops up inside the phone.
  - [ ] The **Appointments Table** on the dashboard immediately adds the new row and **flashes with a green highlight animation**.
  - [ ] The booked slot disappears from Dr. Priya Sharma's open slots.
- [ ] **Cancel the Appointment:** Say *"Actually, please cancel my appointment."*
  - [ ] Agent verifies the number and asks for confirmation.
  - [ ] Say *"Yes, cancel it."*
  - [ ] The row status changes to **Cancelled** with a **red highlight pulse**, and the slot immediately re-opens on the schedule!
- [ ] **Mute & End Call:** Test the microphone mute toggle and click the red **End Call** button to hear the polite disconnect beeps.

---

## Known Limitations

1. **Microphone Permissions:** WebRTC requires microphone permissions. In browsers like Chrome, microphone access requires `localhost` or an `https://` origin.
2. **Free Tier Quotas:** The Google Gemini free API tier has standard rate limits (15 requests per minute). Gemini 2.5 Flash operates comfortably within this quota for individual demo calls.
3. **Local Mock Data:** Appointments and doctor availability are persisted in an SQLite database file (`backend/clinic.db`). Click the **"Reset Data"** button on the dashboard at any time to return the database to its pristine demo seed state.

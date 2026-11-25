# 2-Minute Demo Video Script: Voice AI Doctor Appointment Assistant

**Target Duration:** 2 minutes (120 seconds)  
**Goal:** Demonstrate the voice pipeline, natural conversation, digit-by-digit phone confirmation, real-time booking with dashboard row highlight, and instant cancellation.

---

### Phase 1: Intro & Call Initiation (0:00 – 0:15)
- **On Screen:** Split screen showing the **Apollo Healthcare Clinic Dashboard** (Doctors list on the left, Appointments table on the right).
- **Speaker Action:** Click the **"Try Call"** button. The phone panel slides in, Web Audio ringing tone plays, and state transitions to **Connected**.
- **Bot:**  
  > *"Hello! Thank you for calling Apollo Clinic. I am Aanya, your appointment assistant. How can I help you today?"*

---

### Phase 2: Check Availability (0:15 – 0:45)
- **Caller (You):**  
  > *"Hi Aanya, I'd like to check Dr. Priya Sharma's available slots for tomorrow."*
- **Visual Cue:** The live waveform reacts as you speak. The caller transcript appears in the phone bubble.
- **Bot:**  
  > *"Dr. Priya Sharma has openings tomorrow at 10:30 AM, 11:30 AM, and 2:00 PM. Which time works best for you?"*
- **Visual Cue:** Look at the left column of the dashboard—you can see those exact slots listed under Dr. Priya Sharma.

---

### Phase 3: Choose Slot & Digit-by-Digit Phone Verification (0:45 – 1:15)
- **Caller (You):**  
  > *"Let's go with 10:30 AM, please."*
- **Bot:**  
  > *"Sure! Could you please share your 10-digit mobile number so I can book that for you?"*
- **Caller (You):**  
  > *"My number is 9 8 7 6 5 4 3 2 1 0."*
- **Bot (Enforcing Mandatory Verification Protocol):**  
  > *"Thank you. Just to confirm, is your number 9 8 7 6 5 4 3 2 1 0?"*
- **Caller (You):**  
  > *"Yes, that is correct."*

---

### Phase 4: Atomic Booking & Instant Dashboard Update (1:15 – 1:40)
- **Bot:**  
  > *"Your appointment with Dr. Priya Sharma is confirmed for tomorrow at 10:30 AM. A confirmation has been registered for your phone number."*
- **Visual Cue on Screen:**  
  1. The **Booking Confirmation Card** pops up inside the phone interface.
  2. The **Appointments Table** on the dashboard instantly adds the new row for `98765 43210` and **flashes with a green highlight animation**.
  3. The `10:30 AM` badge on Dr. Priya's schedule disappears in real time!

---

### Phase 5: Fast Cancellation & Reopening Slot (1:40 – 1:55)
- **Caller (You):**  
  > *"Actually, my schedule changed. Can you please cancel my appointment?"*
- **Bot:**  
  > *"I can help you cancel that. To verify, should I cancel the appointment for 9 8 7 6 5 4 3 2 1 0?"*
- **Caller (You):**  
  > *"Yes, please cancel it."*
- **Bot:**  
  > *"Your appointment with Dr. Priya Sharma on 2026-11-25 at 10:30 AM has been cancelled."*
- **Visual Cue on Screen:**  
  1. The row status changes from **Confirmed** to **Cancelled** with a **red highlight pulse**.
  2. The `10:30 AM` slot immediately reappears as open under Dr. Priya's schedule!

---

### Phase 6: Call Wrap Up (1:55 – 2:00)
- **Caller (You):**  
  > *"Thank you, that's all!"*
- **Speaker Action:** Click the red **End Call** button. Disconnect beeps play, call duration is logged, and the phone displays "Call Finished".
- **Wrap-up Sentence:**  
  > *"That demonstrates checking availability, digit-by-digit verification, zero-double-booking prevention, and instant live sync between Pipecat and the React dashboard."*

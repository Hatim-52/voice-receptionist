"""
tools.py - Voice AI Doctor Appointment Assistant Tool Layer.

Contains:
1. Spoken number normalization & validation (words/multipliers to 10-digit standard).
2. Natural date & time resolution (e.g. 'tomorrow', 'Wednesday', '2 pm').
3. The 3 function tools registered with Pipecat / Gemini:
   - check_doctor_availability (filters out slots that have already passed today in Asia/Kolkata)
   - book_appointment (enforces phone_confirmed=True)
   - cancel_appointment (enforces phone_confirmed=True)
4. Live event listener hooks for real-time dashboard updates.
"""

import re
import asyncio
from datetime import date, timedelta, datetime, time as dt_time
from typing import Optional, Dict, Any, List, Callable
from zoneinfo import ZoneInfo
from backend import db

# Server's local timezone
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

def get_now_kolkata() -> datetime:
    """Return the current datetime in Asia/Kolkata timezone."""
    return datetime.now(KOLKATA_TZ)


def is_slot_in_past(target_date_str: str, slot_time_str: str, now: Optional[datetime] = None) -> bool:
    """
    Check if a slot has already passed based on the server's local time (Asia/Kolkata).
    target_date_str: ISO format YYYY-MM-DD
    slot_time_str: '10:30 AM', '02:00 PM', etc.
    """
    if now is None:
        now = get_now_kolkata()
    today_str = now.date().isoformat()
    if target_date_str < today_str:
        return True
    if target_date_str == today_str:
        try:
            slot_t = datetime.strptime(slot_time_str.strip(), "%I:%M %p").time()
            return slot_t <= now.time()
        except ValueError:
            return False
    return False


# In-memory listeners for live event propagation (SSE/WebSocket)
_event_listeners: List[Callable[[Dict[str, Any]], Any]] = []


def register_event_listener(listener: Callable[[Dict[str, Any]], Any]):
    """Register an asynchronous or synchronous listener for live appointment events."""
    if listener not in _event_listeners:
        _event_listeners.append(listener)


def unregister_event_listener(listener: Callable[[Dict[str, Any]], Any]):
    """Unregister an event listener."""
    if listener in _event_listeners:
        _event_listeners.remove(listener)


def notify_event(event_type: str, data: Dict[str, Any]):
    """Broadcast an event to all registered dashboard listeners."""
    payload = {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    for listener in _event_listeners:
        try:
            if asyncio.iscoroutinefunction(listener):
                asyncio.create_task(listener(payload))
            else:
                listener(payload)
        except Exception as e:
            print(f"[tools.py] Error in event listener: {e}")


# ==============================================================================
# Phone Number Normalization
# ==============================================================================

WORD_TO_DIGIT = {
    "zero": "0", "oh": "0", "o": "0",
    "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9"
}

MULTIPLIERS = {
    "double": 2,
    "triple": 3,
    "twice": 2,
    "thrice": 3
}


def normalize_phone_number(raw_input: Any) -> str:
    """
    Normalize spoken or text phone numbers into a 10-digit string.
    Handles words ("nine eight seven..."), multipliers ("double five", "triple zero"),
    country codes (+91 / 91 / 0), spaces, dashes, and parentheses.
    
    Raises ValueError with a user-friendly message if invalid.
    """
    if raw_input is None:
        raise ValueError("Phone number is required.")

    text = str(raw_input).lower().strip()
    # Replace punctuation with spaces
    text = re.sub(r"[-–—,._\(\)\+]", " ", text)
    tokens = text.split()

    digits: List[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Check multiplier words (e.g. 'double five' -> '55', 'triple zero' -> '000')
        if token in MULTIPLIERS and i + 1 < len(tokens):
            mult = MULTIPLIERS[token]
            next_token = tokens[i + 1]
            if next_token in WORD_TO_DIGIT:
                digits.extend([WORD_TO_DIGIT[next_token]] * mult)
                i += 2
                continue
            elif next_token.isdigit() and len(next_token) == 1:
                digits.extend([next_token] * mult)
                i += 2
                continue

        # Check standard number words
        if token in WORD_TO_DIGIT:
            digits.append(WORD_TO_DIGIT[token])
        elif token.isdigit():
            digits.extend(list(token))
        else:
            # Strip non-digits from token if any
            clean_sub = re.sub(r"\D", "", token)
            if clean_sub:
                digits.extend(list(clean_sub))
        i += 1

    num_str = "".join(digits)

    # Handle Indian country code (+91) or leading zero
    if len(num_str) == 12 and num_str.startswith("91"):
        num_str = num_str[2:]
    elif len(num_str) == 11 and num_str.startswith("0"):
        num_str = num_str[1:]

    if len(num_str) != 10:
        raise ValueError(
            f"Invalid phone number '{raw_input}'. Please provide a valid 10-digit mobile number."
        )

    return num_str


def format_number_digit_by_digit(phone_10: str) -> str:
    """Format a 10-digit number separated by spaces for natural speech read-back."""
    return " ".join(list(phone_10))


# ==============================================================================
# Natural Date & Time Resolution
# ==============================================================================

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def resolve_natural_date(raw_date: Optional[str]) -> str:
    """
    Resolve natural language date descriptions to ISO YYYY-MM-DD using Asia/Kolkata date.
    Supports: 'today', 'tomorrow', 'day after tomorrow', weekday names, or YYYY-MM-DD.
    Defaults to today if not provided or unparseable.
    """
    today = get_now_kolkata().date()
    if not raw_date:
        return today.isoformat()

    s = str(raw_date).lower().strip()

    if "today" in s:
        return today.isoformat()
    if "day after tomorrow" in s:
        return (today + timedelta(days=2)).isoformat()
    if "tomorrow" in s:
        return (today + timedelta(days=1)).isoformat()

    # Weekday check
    for idx, day_name in enumerate(WEEKDAYS):
        if day_name in s:
            today_weekday = today.weekday()
            days_ahead = (idx - today_weekday) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week if today is that day and caller asks for it
            return (today + timedelta(days=days_ahead)).isoformat()

    # Attempt ISO format parsing (e.g. 2026-11-25)
    match_iso = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", s)
    if match_iso:
        y, m, d = match_iso.groups()
        try:
            return date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            pass

    # Attempt day-month format (e.g. 25 Nov, 25th November)
    for fmt in ("%d %B", "%d %b", "%d-%m", "%d/%m"):
        try:
            clean_s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)
            parsed = datetime.strptime(clean_s, fmt)
            return date(today.year, parsed.month, parsed.day).isoformat()
        except ValueError:
            pass

    # Default to today if cannot parse
    return today.isoformat()


def resolve_natural_time(raw_time: Optional[str]) -> Optional[str]:
    """
    Normalize various spoken time strings into standard slots:
    ['09:00 AM', '10:30 AM', '11:30 AM', '02:00 PM', '03:30 PM', '05:00 PM']
    """
    if not raw_time:
        return None

    s = str(raw_time).lower().strip()

    # Direct match with standard slots
    for slot in db.STANDARD_SLOTS:
        if slot.lower() == s:
            return slot

    # Match hour & minute patterns
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)

        # Contextual am/pm inference: 9, 10, 11 are AM; 1, 2, 3, 4, 5 are PM
        if not meridiem:
            if 8 <= hour <= 11:
                meridiem = "am"
            elif 1 <= hour <= 6 or hour == 12:
                meridiem = "pm"
            else:
                meridiem = "am"

        formatted = f"{hour:02d}:{minute:02d} {meridiem.upper()}"
        for slot in db.STANDARD_SLOTS:
            if slot == formatted:
                return slot

    # Fuzzy match with slots
    for slot in db.STANDARD_SLOTS:
        slot_clean = slot.replace("0", "").replace(" ", "").lower()
        s_clean = s.replace("0", "").replace(" ", "").lower()
        if s_clean in slot_clean or slot_clean in s_clean:
            return slot

    return raw_time.strip()


# ==============================================================================
# Tool Implementations
# ==============================================================================

def check_doctor_availability(
    doctor_name: Optional[str] = None,
    speciality: Optional[str] = None,
    date: Optional[str] = None,
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Tool 1: Check available slots for a doctor or speciality on a given date.
    MUST NOT return slots whose time has already passed today in Asia/Kolkata timezone.
    Returns 2-3 available slots at a time so the voice agent does not read a long list.
    """
    query = doctor_name or speciality
    target_date = resolve_natural_date(date)

    if not query:
        # Return all available doctors summary
        all_docs = db.get_all_doctors()
        doc_names = [f"{d['name']} ({d['speciality']})" for d in all_docs[:3]]
        return {
            "status": "need_doctor",
            "message": f"We have several specialists available, such as {', '.join(doc_names)}. Which doctor or speciality would you like to see?",
            "sample_doctors": [d["name"] for d in all_docs]
        }

    doctor = db.find_doctor(query)
    if not doctor:
        return {
            "status": "doctor_not_found",
            "message": f"I couldn't find a doctor matching '{query}'. We have General Physicians, Cardiologists, Dermatologists, Pediatricians, Orthopedics, and ENT specialists. Which one would you prefer?"
        }

    # Fetch slots from DB (excluding already booked appointments)
    slots = db.get_doctor_available_slots(doctor["id"], target_date)

    # Filter out slots whose time has already passed today in Asia/Kolkata
    now_kolkata = now or get_now_kolkata()
    today_kolkata_str = now_kolkata.date().isoformat()
    if target_date == today_kolkata_str:
        slots = [slot for slot in slots if not is_slot_in_past(target_date, slot, now=now_kolkata)]

    date_display = target_date
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        today = now_kolkata.date()
        if dt == today:
            date_display = "today"
        elif dt == today + timedelta(days=1):
            date_display = "tomorrow"
        else:
            date_display = dt.strftime("%A, %B %d")
    except Exception:
        pass

    if not slots:
        return {
            "status": "no_slots",
            "doctor": doctor["name"],
            "speciality": doctor["speciality"],
            "date": target_date,
            "available_slots": [],
            "total_available_slots": 0,
            "message": f"{doctor['name']} has no open slots on {date_display}. Would you like to check tomorrow or another day?"
        }

    # Offer at most 2-3 slots for natural voice conversation
    offered_slots = slots[:3]
    slots_str = ", ".join(offered_slots[:-1]) + (" and " + offered_slots[-1] if len(offered_slots) > 1 else offered_slots[0])

    return {
        "status": "available",
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "speciality": doctor["speciality"],
        "date": target_date,
        "date_display": date_display,
        "available_slots": offered_slots,
        "total_available_slots": len(slots),
        "message": f"{doctor['name']} ({doctor['speciality']}) has openings on {date_display} at {slots_str}. Which time works best for you?"
    }


def book_appointment(
    phone_number: str,
    doctor_name: str,
    date: str,
    time: str,
    patient_name: Optional[str] = None,
    phone_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Tool 2: Book an appointment slot for the caller.
    Enforces number confirmation in code: requires phone_confirmed=True, set ONLY after
    the caller says yes to the digit-by-digit readback. If missing or false, returns
    a message instructing the agent to read the number back and ask for confirmation.
    """
    # 1. Validate and normalize phone number
    try:
        normalized_phone = normalize_phone_number(phone_number)
    except ValueError as e:
        return {
            "status": "invalid_phone",
            "error": str(e),
            "message": "I could not verify that phone number. Could you please repeat your 10-digit mobile number?"
        }

    # 2. Enforce explicit phone confirmation before booking
    is_confirmed = (
        phone_confirmed is True or
        (isinstance(phone_confirmed, str) and phone_confirmed.lower() in ("true", "1", "yes"))
    )
    if not is_confirmed:
        digit_str = format_number_digit_by_digit(normalized_phone)
        return {
            "status": "confirmation_required",
            "phone_number": normalized_phone,
            "message": f"Before booking, please read the phone number back digit by digit: {digit_str}, and ask the caller to confirm with a clear 'yes'."
        }

    # 3. Match doctor
    doctor = db.find_doctor(doctor_name)
    if not doctor:
        return {
            "status": "doctor_not_found",
            "error": f"Doctor '{doctor_name}' not found.",
            "message": f"I couldn't find a doctor by the name of {doctor_name}. Could you please specify which doctor or speciality you would like?"
        }

    # 4. Resolve target date and time
    target_date = resolve_natural_date(date)
    target_time = resolve_natural_time(time)
    if not target_time:
        return {
            "status": "invalid_time",
            "error": "Time slot not recognized.",
            "message": f"I didn't catch the time. Available slots for {doctor['name']} include {', '.join(db.STANDARD_SLOTS[:3])}. What time suits you?"
        }

    # 5. Prevent booking slots that have already passed today in Asia/Kolkata
    if is_slot_in_past(target_date, target_time):
        return {
            "status": "slot_in_past",
            "error": f"The slot {target_time} on {target_date} has already passed.",
            "message": f"That time slot has already passed for today. Would you like to check tomorrow or choose an upcoming slot?"
        }

    # 6. Attempt booking in DB
    result = db.book_slot(
        phone_number=normalized_phone,
        doctor_id=doctor["id"],
        doctor_name=doctor["name"],
        target_date=target_date,
        time_slot=target_time,
        patient_name=patient_name or "Caller"
    )

    if not result["success"]:
        return {
            "status": "booking_failed",
            "error": result["error"],
            "message": result["error"]
        }

    appointment = result["appointment"]

    # 7. Broadcast live event to connected frontend dashboard
    notify_event("appointment_booked", appointment)

    # Human-readable confirmation date
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        today = get_now_kolkata().date()
        if dt == today:
            date_readable = "today"
        elif dt == today + timedelta(days=1):
            date_readable = "tomorrow"
        else:
            date_readable = dt.strftime("%A, %B %d")
    except Exception:
        date_readable = target_date

    return {
        "status": "confirmed",
        "appointment_id": appointment["id"],
        "phone_number": normalized_phone,
        "doctor_name": doctor["name"],
        "speciality": doctor["speciality"],
        "date": target_date,
        "date_readable": date_readable,
        "time": target_time,
        "patient_name": appointment.get("patient_name", "Caller"),
        "message": f"Your appointment with {doctor['name']} is confirmed for {date_readable} at {target_time}. A confirmation has been registered for your phone number."
    }


def cancel_appointment(
    phone_number: str,
    phone_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Tool 3: Cancel an existing appointment identified by caller phone number.
    Enforces number confirmation in code: requires phone_confirmed=True, set ONLY after
    the caller says yes to the digit-by-digit readback. If missing or false, returns
    a message instructing the agent to read the number back and ask for confirmation.
    """
    # 1. Validate and normalize phone number
    try:
        normalized_phone = normalize_phone_number(phone_number)
    except ValueError as e:
        return {
            "status": "invalid_phone",
            "error": str(e),
            "message": "I could not find that phone number. Could you please repeat your 10-digit mobile number?"
        }

    # 2. Enforce explicit phone confirmation before cancelling
    is_confirmed = (
        phone_confirmed is True or
        (isinstance(phone_confirmed, str) and phone_confirmed.lower() in ("true", "1", "yes"))
    )
    if not is_confirmed:
        digit_str = format_number_digit_by_digit(normalized_phone)
        return {
            "status": "confirmation_required",
            "phone_number": normalized_phone,
            "message": f"Before cancelling, please read the phone number back digit by digit: {digit_str}, and ask the caller to confirm with a clear 'yes'."
        }

    # 3. Cancel in DB
    result = db.cancel_appointment_by_phone(normalized_phone)

    if not result["success"]:
        return {
            "status": "no_appointment_found",
            "error": result["error"],
            "message": result["error"]
        }

    appointment = result["appointment"]

    # 4. Broadcast live event to connected frontend dashboard
    notify_event("appointment_cancelled", appointment)

    return {
        "status": "cancelled",
        "appointment_id": appointment["id"],
        "doctor_name": appointment["doctor_name"],
        "date": appointment["date"],
        "time": appointment["time"],
        "message": f"Your appointment with {appointment['doctor_name']} on {appointment['date']} at {appointment['time']} has been cancelled."
    }

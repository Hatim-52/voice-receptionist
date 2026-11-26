"""
db.py - SQLite Database & Mock Data Layer for Voice AI Doctor Appointment Assistant.

Provides data storage, seeding, availability querying, and atomic booking/cancellation.
Enforces double-booking prevention at the database level with a unique partial index.
"""

import sqlite3
import os
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "clinic.db")

# Standard slot schedule for doctors across the next 7 days
STANDARD_SLOTS = [
    "09:00 AM",
    "10:30 AM",
    "11:30 AM",
    "02:00 PM",
    "03:30 PM",
    "05:00 PM"
]

SEED_DOCTORS = [
    {
        "id": 1,
        "name": "Dr. Priya Sharma",
        "speciality": "General Physician",
        "experience": "12 years",
        "room": "Room 101",
        "bio": "Primary care, fevers, routine checkups, and chronic disease management."
    },
    {
        "id": 2,
        "name": "Dr. Rajesh Kumar",
        "speciality": "Cardiologist",
        "experience": "16 years",
        "room": "Room 204",
        "bio": "Cardiovascular health, hypertension, ECG evaluation, and chest discomfort."
    },
    {
        "id": 3,
        "name": "Dr. Ananya Patel",
        "speciality": "Dermatologist",
        "experience": "8 years",
        "room": "Room 108",
        "bio": "Skin allergies, acne, eczema, hair loss, and cosmetic dermatology."
    },
    {
        "id": 4,
        "name": "Dr. Suresh Mehta",
        "speciality": "Pediatrician",
        "experience": "14 years",
        "room": "Room 105",
        "bio": "Infant care, child growth monitoring, vaccinations, and pediatric illnesses."
    },
    {
        "id": 5,
        "name": "Dr. Vikram Rao",
        "speciality": "Orthopedic",
        "experience": "11 years",
        "room": "Room 210",
        "bio": "Joint pains, fracture rehabilitation, spine care, and sports injuries."
    },
    {
        "id": 6,
        "name": "Dr. Sunita Nair",
        "speciality": "ENT Specialist",
        "experience": "9 years",
        "room": "Room 112",
        "bio": "Ear infections, sinus congestion, hearing assessment, and throat issues."
    }
]


def get_db_connection() -> sqlite3.Connection:
    """Return a configured SQLite database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset: bool = False):
    """
    Initialize SQLite tables and seed initial mock data.
    If reset=True, drop existing tables first.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if reset:
        cursor.execute("DROP TABLE IF EXISTS appointments")
        cursor.execute("DROP TABLE IF EXISTS doctors")

    # Doctors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        speciality TEXT NOT NULL,
        experience TEXT NOT NULL,
        room TEXT NOT NULL,
        bio TEXT
    )
    """)

    # Appointments Table
    # A single partial unique index prevents double booking of any slot when status is confirmed
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        patient_name TEXT,
        doctor_id INTEGER NOT NULL,
        doctor_name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'confirmed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_active_appointment 
    ON appointments (doctor_id, date, time) 
    WHERE status = 'confirmed'
    """)

    # Seed Doctors if table is empty
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] == 0:
        for doc in SEED_DOCTORS:
            cursor.execute(
                "INSERT INTO doctors (id, name, speciality, experience, room, bio) VALUES (?, ?, ?, ?, ?, ?)",
                (doc["id"], doc["name"], doc["speciality"], doc["experience"], doc["room"], doc["bio"])
            )

    # Seed 2-3 sample appointments if empty
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone()[0] == 0:
        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
        day_after_str = (date.today() + timedelta(days=2)).isoformat()

        sample_appointments = [
            ("9810011223", "Aarav Sharma", 1, "Dr. Priya Sharma", today_str, "09:00 AM", "confirmed"),
            ("9811223344", "Sneha Roy", 2, "Dr. Rajesh Kumar", today_str, "10:30 AM", "confirmed"),
            ("9922334455", "Rohan Verma", 3, "Dr. Ananya Patel", tomorrow_str, "02:00 PM", "confirmed"),
            ("9733445566", "Meera Iyer", 5, "Dr. Vikram Rao", day_after_str, "11:30 AM", "confirmed"),
        ]

        for apt in sample_appointments:
            cursor.execute(
                """
                INSERT OR IGNORE INTO appointments 
                (phone, patient_name, doctor_id, doctor_name, date, time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                apt
            )

    conn.commit()
    conn.close()


def get_all_doctors() -> List[Dict[str, Any]]:
    """Return all doctors with their metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, speciality, experience, room, bio FROM doctors ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def find_doctor(name_or_speciality: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Fuzzy/flexible match a doctor by name or speciality.
    E.g., 'Priya', 'Dr. Priya', 'Cardiologist', 'heart', 'skin', 'children'
    """
    if not name_or_speciality:
        return None

    query = name_or_speciality.strip().lower()
    # Normalize common doctor terms
    alias_map = {
        "skin": "Dermatologist",
        "dermatology": "Dermatologist",
        "heart": "Cardiologist",
        "cardio": "Cardiologist",
        "child": "Pediatrician",
        "children": "Pediatrician",
        "baby": "Pediatrician",
        "pediatric": "Pediatrician",
        "bone": "Orthopedic",
        "bones": "Orthopedic",
        "joint": "Orthopedic",
        "general": "General Physician",
        "physician": "General Physician",
        "fever": "General Physician",
        "ear": "ENT Specialist",
        "nose": "ENT Specialist",
        "throat": "ENT Specialist",
        "ent": "ENT Specialist"
    }

    doctors = get_all_doctors()

    # 1. Exact or substring match in doctor name
    for doc in doctors:
        doc_name_lower = doc["name"].lower()
        if query in doc_name_lower or doc_name_lower in query:
            return doc

    # 2. Match in speciality
    for doc in doctors:
        spec_lower = doc["speciality"].lower()
        if query in spec_lower or spec_lower in query:
            return doc

    # 3. Alias dictionary check
    for keyword, target_spec in alias_map.items():
        if keyword in query:
            for doc in doctors:
                if doc["speciality"].lower() == target_spec.lower():
                    return doc

    return None


def get_doctor_available_slots(doctor_id: int, target_date: str) -> List[str]:
    """
    Return the list of available slot times for a doctor on a specific date (YYYY-MM-DD).
    Filters out slots that already have a confirmed appointment.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT time FROM appointments 
        WHERE doctor_id = ? AND date = ? AND status = 'confirmed'
        """,
        (doctor_id, target_date)
    )
    booked_times = {row["time"] for row in cursor.fetchall()}
    conn.close()

    return [slot for slot in STANDARD_SLOTS if slot not in booked_times]


def get_doctors_with_slots(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Return all doctors, each with an availability map for the next N days.
    Used by the dashboard REST endpoint to display live doctor schedules.
    """
    doctors = get_all_doctors()
    today = date.today()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(days_ahead)]

    result = []
    for doc in doctors:
        availability = {}
        for d in dates:
            availability[d] = get_doctor_available_slots(doc["id"], d)
        
        doc_data = dict(doc)
        doc_data["available_dates"] = dates
        doc_data["slots_by_date"] = availability
        # Quick summary of today and tomorrow's availability
        doc_data["today_slots"] = availability.get(dates[0], [])
        doc_data["tomorrow_slots"] = availability.get(dates[1], []) if len(dates) > 1 else []
        result.append(doc_data)

    return result


def get_all_appointments() -> List[Dict[str, Any]]:
    """Return all appointments ordered by creation time descending."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, phone, patient_name, doctor_id, doctor_name, date, time, status, created_at
        FROM appointments
        ORDER BY id DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_active_appointment_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """Find the most recent active confirmed appointment for a phone number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, phone, patient_name, doctor_id, doctor_name, date, time, status, created_at
        FROM appointments
        WHERE phone = ? AND status = 'confirmed'
        ORDER BY date ASC, time ASC
        LIMIT 1
        """,
        (phone_number,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def book_slot(
    phone_number: str,
    doctor_id: int,
    doctor_name: str,
    target_date: str,
    time_slot: str,
    patient_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Atomically book an appointment slot.
    Returns dictionary with success status and appointment data or error.
    """
    # Verify slot availability
    available_slots = get_doctor_available_slots(doctor_id, target_date)
    if time_slot not in available_slots:
        return {
            "success": False,
            "error": f"The slot at {time_slot} on {target_date} with {doctor_name} is already booked or unavailable."
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO appointments (phone, patient_name, doctor_id, doctor_name, date, time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
            """,
            (
                phone_number,
                patient_name or "Caller",
                doctor_id,
                doctor_name,
                target_date,
                time_slot
            )
        )
        appointment_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        created = dict(cursor.fetchone())
        conn.close()
        return {"success": True, "appointment": created}
    except sqlite3.IntegrityError:
        conn.close()
        return {
            "success": False,
            "error": f"That slot at {time_slot} on {target_date} with {doctor_name} was just booked. Please pick another slot."
        }
    except Exception as e:
        conn.close()
        return {"success": False, "error": f"Database error while booking: {str(e)}"}


def cancel_appointment_by_phone(phone_number: str) -> Dict[str, Any]:
    """
    Cancel the active appointment associated with this phone number.
    Returns success status, cancelled appointment details, or error message.
    """
    active_apt = get_active_appointment_by_phone(phone_number)
    if not active_apt:
        return {
            "success": False,
            "error": f"No active confirmed appointment found for phone number ending in {phone_number[-4:]}."
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE appointments
            SET status = 'cancelled'
            WHERE id = ?
            """,
            (active_apt["id"],)
        )
        conn.commit()
        active_apt["status"] = "cancelled"
        conn.close()
        return {
            "success": True,
            "appointment": active_apt,
            "message": f"Appointment with {active_apt['doctor_name']} on {active_apt['date']} at {active_apt['time']} has been successfully cancelled."
        }
    except Exception as e:
        conn.close()
        return {"success": False, "error": f"Database error while cancelling: {str(e)}"}


if __name__ == "__main__":
    init_db(reset=True)
    print("Database initialized successfully!")
    docs = get_doctors_with_slots()
    print(f"Loaded {len(docs)} doctors.")
    print("Sample doctor slots for today:", docs[0]["name"], docs[0]["today_slots"])
    apts = get_all_appointments()
    print(f"Loaded {len(apts)} initial appointments.")

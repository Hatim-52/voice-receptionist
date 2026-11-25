"""
test_tools.py - Unit and Integration Tests for tools.py and db.py.
Tests:
1. Spoken number normalization with single digits, words, "double", and "triple".
2. check_doctor_availability filtering out slots that have already passed today (Asia/Kolkata).
3. Number confirmation enforcement: book_appointment and cancel_appointment require phone_confirmed=True.
4. Slot double-booking prevention, cancellation, and live event broadcasting.
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from backend import db, tools
import sys

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

def run_tests():
    print("==================================================================")
    print("=== 1. Testing Phone Normalization (with 'double' and 'triple') ===")
    print("==================================================================")
    
    # Test cases including standard, word-based, and double/triple multipliers
    test_cases = [
        ("9876543210", "9876543210"),
        ("+91 9876543210", "9876543210"),
        ("09876543210", "9876543210"),
        ("98765 43210", "9876543210"),
        ("nine eight seven six five four three two one zero", "9876543210"),
        # Spoken with 'double' and 'triple':
        ("nine eight double seven five four triple zero one", "9877540001"),
        ("nine double eight seven triple six five four three", "9887666543"),
        ("nine eight seven double six five four three two one", "9876654321"),
        ("plus nine one double nine eight eight seven triple two one", "998872221"), # 9 digits -> will test below with 10 digits
        ("double nine eight seven triple six five four three zero", "99876665430"), # 11 digits with 0
    ]

    # Specific 10-digit cases with double and triple
    double_triple_cases = [
        ("nine eight double seven five four triple zero one", "9877540001"),
        ("nine double eight seven triple six five four three", "9887666543"),
        ("double nine eight seven triple six five four three", "9987666543"),
        ("plus nine one nine eight double zero seven triple five one", "980075551"), # 91 + 10 digits
        ("nine eight seven six five double four triple three", "9876544333"),
    ]

    print("\n--- Verifying Spoken Numbers with 'double' and 'triple' (Printing Full Input Strings) ---")
    for raw_input, expected in double_triple_cases:
        # If +91 with 10 digits
        if "plus nine one" in raw_input and expected == "980075551":
            raw_input = "plus nine one nine eight double zero seven triple five one two"
            expected = "9800755512"

        res = tools.normalize_phone_number(raw_input)
        print(f"  [FULL INPUT]: \"{raw_input}\"")
        print(f"  [NORMALIZED]: \"{res}\"")
        assert res == expected, f"Failed for full input '{raw_input}': got '{res}', expected '{expected}'"
        print(f"  [PASS] Successfully matched: {expected}\n")

    # Standard normalization checks
    standard_cases = [
        ("9876543210", "9876543210"),
        ("+91 9876543210", "9876543210"),
        ("09876543210", "9876543210"),
        ("98765 43210", "9876543210"),
        ("nine eight seven six five four three two one zero", "9876543210"),
    ]
    for raw, expected in standard_cases:
        res = tools.normalize_phone_number(raw)
        assert res == expected, f"Failed for {raw}: got {res}, expected {expected}"
        print(f"  [PASS] Standard input: '{raw}' -> {res}")

    # Test invalid phones
    invalid_cases = ["12345", "not a phone", "1234567890123"]
    for inv in invalid_cases:
        try:
            tools.normalize_phone_number(inv)
            assert False, f"Should have failed for {inv}"
        except ValueError:
            print(f"  [PASS] Correctly rejected invalid input: '{inv}'")

    print("\n==================================================================")
    print("=== 2. Resetting and Initializing Database                     ===")
    print("==================================================================")
    db.init_db(reset=True)
    doctors = db.get_all_doctors()
    assert len(doctors) == 6, f"Expected 6 doctors, found {len(doctors)}"
    print(f"  [PASS] Seeded {len(doctors)} doctors successfully.")

    print("\n==================================================================")
    print("=== 3. Testing check_doctor_availability (Asia/Kolkata Filter) ===")
    print("==================================================================")
    now_kolkata = tools.get_now_kolkata()
    print(f"  Current Server Time (Asia/Kolkata): {now_kolkata.strftime('%Y-%m-%d %I:%M %p')}")

    # 3A. Test simulated time today at 11:00 AM
    # At 11:00 AM, slots '09:00 AM' and '10:30 AM' MUST NOT be returned.
    # Future slots '11:30 AM', '02:00 PM', '03:30 PM', '05:00 PM' SHOULD be returned.
    simulated_11am = datetime(now_kolkata.year, now_kolkata.month, now_kolkata.day, 11, 0, 0, tzinfo=KOLKATA_TZ)
    avail_sim = tools.check_doctor_availability(doctor_name="Dr. Priya", date="today", now=simulated_11am)
    print(f"  Simulated 11:00 AM check for today: {avail_sim['available_slots']}")
    assert "09:00 AM" not in avail_sim["available_slots"], "09:00 AM should have passed by 11:00 AM"
    assert "10:30 AM" not in avail_sim["available_slots"], "10:30 AM should have passed by 11:00 AM"
    for slot in avail_sim["available_slots"]:
        slot_t = datetime.strptime(slot, "%I:%M %p").time()
        assert slot_t > simulated_11am.time(), f"Slot {slot} should be strictly after 11:00 AM"
    print(f"  [PASS] Past slots (09:00 AM, 10:30 AM) successfully filtered out for today at 11:00 AM.")

    # 3B. Test simulated time today at 05:30 PM (all standard slots have passed)
    simulated_530pm = datetime(now_kolkata.year, now_kolkata.month, now_kolkata.day, 17, 30, 0, tzinfo=KOLKATA_TZ)
    avail_passed = tools.check_doctor_availability(doctor_name="Dr. Priya", date="today", now=simulated_530pm)
    assert avail_passed["status"] == "no_slots", f"Expected no_slots at 5:30 PM, got {avail_passed['status']}"
    assert len(avail_passed["available_slots"]) == 0
    print(f"  [PASS] Correctly returns no_slots when all slots have passed today: \"{avail_passed['message']}\"")

    # 3C. Check availability for tomorrow (all open future slots available)
    avail_tomorrow = tools.check_doctor_availability(doctor_name="Dr. Priya", date="tomorrow")
    assert avail_tomorrow["status"] == "available", f"Expected available for tomorrow: {avail_tomorrow}"
    assert len(avail_tomorrow["available_slots"]) > 0
    print(f"  [PASS] Tomorrow's availability: {avail_tomorrow['available_slots']}")

    # 3D. Check by speciality alias
    avail_cardio = tools.check_doctor_availability(speciality="heart doctor", date="tomorrow")
    assert avail_cardio["status"] == "available"
    assert avail_cardio["doctor_name"] == "Dr. Rajesh Kumar"
    print(f"  [PASS] Matched 'heart doctor' to {avail_cardio['doctor_name']}")

    print("\n==================================================================")
    print("=== 4. Testing Event Listener Registration                     ===")
    print("==================================================================")
    events_received = []
    def on_event(evt):
        events_received.append(evt)

    tools.register_event_listener(on_event)
    print("  [PASS] Registered live event listener.")

    print("\n==================================================================")
    print("=== 5. Testing Enforced Number Confirmation in book_appointment ===")
    print("==================================================================")
    phone_spoken = "nine eight double seven five four triple zero one"
    normalized_expected = "9877540001"

    # 5A. Attempt booking WITHOUT confirmation (phone_confirmed=False)
    unconfirmed_res = tools.book_appointment(
        phone_number=phone_spoken,
        doctor_name="Dr. Ananya Patel",
        date="tomorrow",
        time="10:30 AM",
        patient_name="Rahul Verma",
        phone_confirmed=False
    )
    print(f"  [UNCONFIRMED ATTEMPT]: Status = {unconfirmed_res['status']}")
    print(f"  [MESSAGE TO AGENT]: \"{unconfirmed_res['message']}\"")
    assert unconfirmed_res["status"] == "confirmation_required", "Should block booking without confirmation"
    assert "digit by digit" in unconfirmed_res["message"]
    assert unconfirmed_res["phone_number"] == normalized_expected
    assert len(events_received) == 0, "No event should be broadcast when booking is blocked"
    print(f"  [PASS] Successfully blocked booking when phone_confirmed is False.")

    # 5B. Attempt booking WITH phone_confirmed=True (after caller says yes)
    confirmed_res = tools.book_appointment(
        phone_number=phone_spoken,
        doctor_name="Dr. Ananya Patel",
        date="tomorrow",
        time="10:30 AM",
        patient_name="Rahul Verma",
        phone_confirmed=True
    )
    print(f"\n  [CONFIRMED ATTEMPT]: Status = {confirmed_res['status']}")
    print(f"  [MESSAGE TO CALLER]: \"{confirmed_res['message']}\"")
    assert confirmed_res["status"] == "confirmed", f"Booking should succeed: {confirmed_res}"
    assert confirmed_res["phone_number"] == normalized_expected
    assert len(events_received) == 1, "Expected 1 event received"
    assert events_received[0]["event"] == "appointment_booked"
    print(f"  [PASS] Booking succeeded and event broadcasted!")

    print("\n==================================================================")
    print("=== 6. Testing Double Booking Prevention                       ===")
    print("==================================================================")
    double_res = tools.book_appointment(
        phone_number="9999988888",
        doctor_name="Dr. Ananya Patel",
        date="tomorrow",
        time="10:30 AM",
        patient_name="Second Caller",
        phone_confirmed=True
    )
    assert double_res["status"] == "booking_failed", f"Double booking should fail: {double_res}"
    print(f"  [PASS] Prevented double-booking: {double_res['message']}")

    print("\n==================================================================")
    print("=== 7. Testing Enforced Number Confirmation in cancel_appointment =")
    print("==================================================================")
    # 7A. Attempt cancellation WITHOUT confirmation (phone_confirmed=False)
    unconfirmed_cancel = tools.cancel_appointment(
        phone_number=normalized_expected,
        phone_confirmed=False
    )
    print(f"  [UNCONFIRMED CANCEL ATTEMPT]: Status = {unconfirmed_cancel['status']}")
    print(f"  [MESSAGE TO AGENT]: \"{unconfirmed_cancel['message']}\"")
    assert unconfirmed_cancel["status"] == "confirmation_required", "Should block cancellation without confirmation"
    assert "digit by digit" in unconfirmed_cancel["message"]
    print(f"  [PASS] Successfully blocked cancellation when phone_confirmed is False.")

    # 7B. Attempt cancellation WITH phone_confirmed=True (after caller says yes)
    confirmed_cancel = tools.cancel_appointment(
        phone_number=normalized_expected,
        phone_confirmed=True
    )
    print(f"\n  [CONFIRMED CANCEL ATTEMPT]: Status = {confirmed_cancel['status']}")
    print(f"  [MESSAGE TO CALLER]: \"{confirmed_cancel['message']}\"")
    assert confirmed_cancel["status"] == "cancelled", f"Cancellation should succeed: {confirmed_cancel}"
    assert len(events_received) == 2, "Expected 2 events (booked + cancelled)"
    assert events_received[1]["event"] == "appointment_cancelled"
    print(f"  [PASS] Cancellation succeeded and event broadcasted!")

    print("\n==================================================================")
    print("=== 8. Testing Cancel When None Exists                         ===")
    print("==================================================================")
    cancel_none = tools.cancel_appointment(
        phone_number=normalized_expected,
        phone_confirmed=True
    )
    assert cancel_none["status"] == "no_appointment_found", f"Expected no_appointment_found, got: {cancel_none}"
    print(f"  [PASS] Correctly handled cancellation with no active appointment: \"{cancel_none['message']}\"")

    print("\n==================================================================")
    print("=== ALL TESTS PASSED WITH 100% SUCCESS!                        ===")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()

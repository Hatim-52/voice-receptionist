import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\hatim\.gemini\antigravity\brain\0931699a-7329-48f5-98ab-16050dec0fde"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

os.makedirs(ARTIFACT_DIR, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)

        # 1. Desktop Dashboard (1440x960)
        p1 = browser.new_page(viewport={'width': 1440, 'height': 960})
        p1.goto('http://127.0.0.1:5173')
        p1.wait_for_selector('text=Dr. Priya Sharma', timeout=10000)
        time.sleep(0.5)
        path1 = os.path.join(ARTIFACT_DIR, "dashboard_desktop.png")
        p1.screenshot(path=path1)
        print("Captured:", path1)
        p1.close()

        # 2. Booked Highlight Pulse
        p2 = browser.new_page(viewport={'width': 1440, 'height': 960})
        p2.goto('http://127.0.0.1:5173/?demo=booked')
        p2.wait_for_selector('text=Rahul Sharma', timeout=10000)
        time.sleep(0.3)
        path2 = os.path.join(ARTIFACT_DIR, "dashboard_booked_highlight.png")
        p2.screenshot(path=path2)
        print("Captured:", path2)
        p2.close()

        # 3. Call Screen Mid-call (transcript + waveform)
        p3 = browser.new_page(viewport={'width': 1440, 'height': 960})
        p3.goto('http://127.0.0.1:5173/?demo=midcall')
        p3.wait_for_selector('text=Apollo Reception Desk', timeout=10000)
        time.sleep(0.6)
        path3 = os.path.join(ARTIFACT_DIR, "call_screen_midcall.png")
        p3.screenshot(path=path3)
        print("Captured:", path3)
        p3.close()

        # 4. Booking Confirmation Card Inside Phone
        p4 = browser.new_page(viewport={'width': 1440, 'height': 960})
        p4.goto('http://127.0.0.1:5173/?demo=booking-card')
        p4.wait_for_selector('text=Appointment Confirmed', timeout=10000)
        time.sleep(0.6)
        path4 = os.path.join(ARTIFACT_DIR, "call_screen_booking_card.png")
        p4.screenshot(path=path4)
        print("Captured:", path4)
        p4.close()

        # 5. Mobile View (390px)
        p5 = browser.new_page(viewport={'width': 390, 'height': 844})
        p5.goto('http://127.0.0.1:5173')
        p5.wait_for_selector('text=Dr. Priya Sharma', timeout=10000)
        time.sleep(0.5)
        path5 = os.path.join(ARTIFACT_DIR, "dashboard_mobile.png")
        p5.screenshot(path=path5)
        print("Captured:", path5)
        p5.close()

        # 6. Mobile Mid-call View (390px)
        p6 = browser.new_page(viewport={'width': 390, 'height': 844})
        p6.goto('http://127.0.0.1:5173/?demo=booking-card')
        p6.wait_for_selector('text=Appointment Confirmed', timeout=10000)
        time.sleep(0.5)
        path6 = os.path.join(ARTIFACT_DIR, "call_screen_mobile_midcall.png")
        p6.screenshot(path=path6)
        print("Captured:", path6)
        p6.close()

        browser.close()
        print("All screenshots successfully captured!")

if __name__ == '__main__':
    run()

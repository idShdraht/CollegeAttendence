from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import traceback
import json
import os
import re
import requests # BUG FIX: Re-integrated the essential requests library.

print("J.A.R.V.I.S. Monarch Engine: Initializing...")

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'jarvis-secret-key-for-monarch'
CORS(app, supports_credentials=True, origins=["*"]) 

# --- Configuration ---
AIMS_BASE_URL = "https://aims.rkmvc.ac.in"
SESSION_FILE = "session_monarch.json"

@app.errorhandler(500)
def internal_server_error(e):
    traceback.print_exc()
    return jsonify(error="J.A.R.V.I.S. Core Systems Failure: A critical, unhandled error occurred."), 500

def scrape_with_cookies(session_data):
    """Scrapes all data points using a saved session."""
    print("J.A.R.V.I.S. LOG: Attempting silent multi-module data acquisition.")
    s = requests.Session()
    for cookie in session_data['cookies']:
        s.cookies.set(cookie['name'], cookie['value'])
    
    dashboard_res = s.get(f"{AIMS_BASE_URL}/student/")
    dashboard_res.raise_for_status()
    if "loginPage" in dashboard_res.url:
        print("J.A.R.V.I.S. LOG: Session key has expired.")
        return None 
    
    attendance_html = s.get(f"{AIMS_BASE_URL}/student/AttndReport").text
    timetable_html = s.get(f"{AIMS_BASE_URL}/student/timetable").text

    print("J.A.R.V.I.S. LOG: Silent acquisition successful. Parsing modules.")
    
    full_data = {
        "attendanceData": parse_attendance_data(attendance_html, session_data['rollNo']),
        "timetableData": parse_timetable_data(timetable_html)
    }
    return full_data

@app.route('/api/check-session', methods=['GET'])
def check_session():
    """Checks for a valid saved session and returns data if available."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
            scraped_data = scrape_with_cookies(session_data)
            if scraped_data:
                return jsonify(scraped_data)
            else:
                os.remove(SESSION_FILE)
        except (json.JSONDecodeError, FileNotFoundError):
             if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            
    return jsonify({"status": "needs_login"})

@app.route('/api/initiate-login', methods=['GET'])
def initiate_login():
    """Launches browser for a full manual login and captures the session key."""
    driver = None
    try:
        print("J.A.R.V.I.S. LOG: Launching visible browser for manual human authentication.")
        options = webdriver.ChromeOptions()
        options.add_argument("window-size=1200,800")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        
        driver.get(f"{AIMS_BASE_URL}/student/loginPage")
        
        print("J.A.R.V.I.S. LOG: Ceding control to human operator. Awaiting successful login...")
        
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Sign out')]"))
        )
        
        print("J.A.R.V.I.S. LOG: Human authentication successful. Acquiring user identity and session key.")
        
        page_source = driver.page_source
        roll_no_match = re.search(r'(\d{13,})', page_source)
        if not roll_no_match:
            welcome_match = re.search(r'Welcome,?\s*([A-Z\s.-]+)\(?,?\s*(\d+)', page_source, re.IGNORECASE)
            if welcome_match:
                roll_no = welcome_match.group(2)
            else:
                 raise ValueError("Could not automatically determine Roll Number from the dashboard.")
        else:
            roll_no = roll_no_match.group(1)

        print(f"J.A.R.V.I.S. LOG: User identity confirmed. Roll Number: {roll_no}")
        
        cookies = driver.get_cookies()
        with open(SESSION_FILE, 'w') as f:
            json.dump({'rollNo': roll_no, 'cookies': cookies}, f)
        
        print("J.A.R.V.I.S. LOG: Session key secured. Beginning multi-module data extraction.")
        
        driver.get(f"{AIMS_BASE_URL}/student/AttndReport")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        attendance_html = driver.page_source

        driver.get(f"{AIMS_BASE_URL}/student/timetable")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        timetable_html = driver.page_source
        
        full_data = {
            "attendanceData": parse_attendance_data(attendance_html, roll_no),
            "timetableData": parse_timetable_data(timetable_html)
        }
        return jsonify(full_data)

    except TimeoutException:
        return jsonify({"error": "Manual login timed out."}), 408
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"A critical error occurred: {e}"}), 500
    finally:
        if driver:
            driver.quit()

def parse_attendance_data(html_content, roll_no):
    soup = BeautifulSoup(html_content, 'html.parser')
    SUBJECT_COLUMN = 2; HELD_HOURS_COLUMN = 6; ATTENDED_HOURS_COLUMN = 7
    subjects = []; total_held_hours = 0; total_attended_hours = 0
    attendance_table = soup.find('table', class_='table-bordered')
    if not attendance_table: raise ValueError("Could not find attendance table.")
    table_rows = attendance_table.find('tbody').find_all('tr')
    for row in table_rows:
        cols = row.find_all('td')
        if len(cols) > max(SUBJECT_COLUMN, HELD_HOURS_COLUMN, ATTENDED_HOURS_COLUMN):
            try:
                subject_name = cols[SUBJECT_COLUMN].text.strip()
                held = float(cols[HELD_HOURS_COLUMN].text.strip())
                attended = float(cols[ATTENDED_HOURS_COLUMN].text.strip())
                subjects.append({"name": subject_name, "held": held, "attended": attended})
                total_held_hours += held; total_attended_hours += attended
            except (ValueError, IndexError): continue
    overall_percentage = (total_attended_hours / total_held_hours) * 100 if total_held_hours > 0 else 0
    return { "rollNo": roll_no, "overallAttendance": round(overall_percentage, 2), "subjects": subjects }

def parse_timetable_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    timetable = {"headers": [], "rows": []}
    table = soup.find('table', class_='table-bordered')
    if not table: return timetable
    header_row = table.find('thead').find('tr')
    for th in header_row.find_all('th'):
        timetable["headers"].append(th.text.strip())
    body_rows = table.find('tbody').find_all('tr')
    for row in body_rows:
        time_slot_data = []
        for td in row.find_all('td'):
            class_info = ' '.join(td.stripped_strings)
            time_slot_data.append(class_info if class_info else "---")
        timetable["rows"].append(time_slot_data)
    return timetable

print("J.A.R.V.I.S. Monarch Engine: All systems nominal. Engaging server.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

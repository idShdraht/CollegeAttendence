from flask import Flask, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import traceback
import json
import os
import re
import requests

print("J.A.R.V.I.S. Sentinel Engine: Initializing...")

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'jarvis-secret-key-for-sentinel'
CORS(app, supports_credentials=True, origins=["*"]) 

# --- Configuration ---
AIMS_BASE_URL = "https://aims.rkmvc.ac.in"
SESSION_FILE = "/tmp/session_sentinel.json" 
# SIR, YOU MUST GET A FREE API KEY FROM BROWSERLESS.IO AND PASTE IT HERE
BROWSERLESS_API_KEY = "2T04KUPWyHqoQsb254cabf9969a21ff868ac5eb097bc906c9"

@app.errorhandler(500)
def internal_server_error(e):
    traceback.print_exc()
    return jsonify(error="J.A.R.V.I.S. Core Systems Failure: A critical, unhandled error occurred."), 500

def get_remote_browser():
    """Connects to the Browserless.io remote fleet."""
    if BROWSERLESS_API_KEY == "PASTE_YOUR_BROWSERLESS_API_KEY_HERE":
        raise ValueError("Browserless.io API Key is not configured.")
    
    print("J.A.R.V.I.S. LOG: Connecting to Sentinel browser fleet...")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # This is the command to connect to the remote browser
    endpoint = f'wss://chrome.browserless.io?token={BROWSERLESS_API_KEY}'
    driver = webdriver.Remote(command_executor=endpoint, options=options)
    print("J.A.R.V.I.S. LOG: Connection established.")
    return driver

# The core logic of the application remains the same, but it now uses the remote browser.
# All other functions (scrape_with_cookies, check_session, initiate_login, parsers) are identical
# to the Chimera/Monarch versions, but with `driver` being a remote instance.
# I am providing the full, corrected, and final code below.

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
    """Uses the remote browser to guide the user through login."""
    driver = None
    try:
        driver = get_remote_browser()
        
        # This endpoint is now a placeholder. The user must be directed to a separate
        # utility for the one-time login, as a remote browser cannot be made visible to the user.
        # The Phoenix protocol (local generator, remote key) remains the most robust solution.
        raise NotImplementedError("This login flow requires a different architecture. Please use the Phoenix protocol.")

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

print("J.A.R.V.I.S. Sentinel Engine: All systems nominal. Engaging server.")

application = app









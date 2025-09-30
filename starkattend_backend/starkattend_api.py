from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import traceback
import json
import requests
import os
import time
import base64
import cv2
import numpy as np
from PIL import Image
from io import BytesIO

# ---------- CONFIG ----------
AIMS_BASE_URL = "https://aims.rkmvc.ac.in"
BROWSERLESS_API_KEY = os.environ.get("BROWSERLESS_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")
DEFAULT_DEBUG = True
# ----------------------------

print("J.A.R.V.I.S. Sentinel Engine: Initializing...")

app = Flask(__name__)
app.secret_key = 'jarvis-secret-key-for-sentinel'

# --- DEFINITIVE CORS CONFIGURATION ---
# This explicitly tells the server to trust your live frontend application.
origins = [
    "https://admirable-narwhal-ef8182.netlify.app",
    "https://astounding-creponne-c164b9.netlify.app",
    "http://localhost:3000", # For any future local testing
]
CORS(app, supports_credentials=True, origins=origins)

@app.errorhandler(500)
def internal_server_error(e):
    traceback.print_exc()
    return jsonify(error="J.A.R.V.I.S. Core Systems Failure: A critical, unhandled error occurred."), 500

def get_remote_browser():
    """Connects to the Browserless.io remote fleet (HTTPS endpoint)."""
    if not BROWSERLESS_API_KEY:
        raise ValueError("Browserless.io API Key is not configured on the server.")
    
    print("J.A.R.V.I.S. LOG: Connecting to Sentinel browser fleet...")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")

    # --- DEFINITIVE FIX: Use the correct HTTPS endpoint for the command executor ---
    endpoint = f'https://chrome.browserless.io/webdriver?token={BROWSERLESS_API_KEY}'

    driver = webdriver.Remote(
        command_executor=endpoint,
        options=options
    )
    print("J.A.R.V.I.S. LOG: Connection established.")
    return driver

def preprocess_captcha(image_bytes, debug=DEFAULT_DEBUG):
    """Preprocesses image bytes for the AI model."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode captcha image bytes.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_img = Image.fromarray(thresh)
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    processed_bytes = buf.getvalue()

    if debug and os.access('.', os.W_OK):
        try:
            pil_img.save("debug_captcha.png")
            print("J.A.R.V.I.S. DEBUG: Preprocessed captcha saved as debug_captcha.png")
        except Exception:
            pass

    return processed_bytes

def solve_captcha_with_service(image_bytes, debug=DEFAULT_DEBUG):
    """Sends a preprocessed captcha to a Hugging Face model for solving."""
    if not HF_API_KEY:
        raise ValueError("Hugging Face API Key is not configured on the server.")

    processed_bytes = preprocess_captcha(image_bytes, debug=debug)
    image_b64 = base64.b64encode(processed_bytes).decode("utf-8")

    prompt = "Solve the captcha in this image. Just tell the solution for the captcha, no other words, no explanation."
    payload = { "inputs": { "messages": [ {"role": "system", "content": "You are a captcha solver."}, {"role": "user", "content": prompt}, {"role": "user", "content": f"data:image/png;base64,{image_b64}"} ] } }
    headers = { "Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json" }

    print("J.A.R.V.I.S. LOG: Sending captcha to LLM via Hugging Face inference...")
    try:
        resp = requests.post("https://api-inference.huggingface.co/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        captcha_text = (result.get("choices")[0].get("message").get("content")).strip()
        if not captcha_text:
            raise RuntimeError(f"Could not parse LLM response for captcha. Full response: {result}")

        captcha_text = captcha_text.splitlines()[0].strip()
        print(f"J.A.R.V.I.S. LOG: Captcha solved as '{captcha_text}'")
        return captcha_text
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError("Captcha solving with LLM failed.") from e

def js_set_value_and_dispatch(driver, element, value):
    """Sets an element's value via JS to mimic user input."""
    script = "(el, val) => { el.focus(); el.value = val; el.dispatchEvent(new Event('input', { bubbles: true})); el.dispatchEvent(new Event('change', { bubbles: true})); }"
    driver.execute_script(script, element, value)

@app.route('/api/scrape', methods=['POST'])
def scrape_data():
    driver = None
    try:
        payload = request.get_json(force=True)
        roll_no, password = payload.get('rollNo'), payload.get('password')
        if not roll_no or not password:
            return jsonify({"error": "rollNo and password are required."}), 400

        driver = get_remote_browser()
        driver.get(f"{AIMS_BASE_URL}/student/loginPage")
        wait = WebDriverWait(driver, 20)

        student_no_el = wait.until(EC.presence_of_element_located((By.NAME, "studentNo")))
        password_el = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        captcha_el = wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'captcha')]")))
        
        js_set_value_and_dispatch(driver, student_no_el, roll_no)
        js_set_value_and_dispatch(driver, password_el, password)
        
        captcha_solution = solve_captcha_with_service(captcha_el.screenshot_as_png())
        
        captcha_input_el = driver.find_element(By.NAME, 'captcha')
        js_set_value_and_dispatch(driver, captcha_input_el, captcha_solution)
        
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        WebDriverWait(driver, 12).until(EC.url_contains("dashboard"))
        
        print("J.A.R.V.I.S. LOG: Login successful; extracting data.")
        driver.get(f"{AIMS_BASE_URL}/student/AttndReport")
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        attendance_html = driver.page_source

        driver.get(f"{AIMS_BASE_URL}/student/timetable")
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        timetable_html = driver.page_source

        return jsonify({
            "attendanceData": parse_attendance_data(attendance_html, roll_no),
            "timetableData": parse_timetable_data(timetable_html)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred on the backend.", "detail": str(e)}), 500
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass

def parse_attendance_data(html_content, roll_no):
    soup = BeautifulSoup(html_content, 'html.parser')
    subjects = []; total_held_hours = 0; total_attended_hours = 0
    table = soup.find('table', class_='table-bordered')
    if not table or not table.tbody: raise ValueError("Could not find attendance table.")
    for row in table.tbody.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 7:
            try:
                held = float(cols[6].text.strip()); attended = float(cols[7].text.strip())
                subjects.append({"name": cols[2].text.strip(), "held": held, "attended": attended})
                total_held_hours += held; total_attended_hours += attended
            except (ValueError, IndexError): continue
    percent = (total_attended_hours / total_held_hours) * 100 if total_held_hours > 0 else 0
    return { "rollNo": roll_no, "overallAttendance": round(percent, 2), "subjects": subjects }

def parse_timetable_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    timetable = {"headers": [], "rows": []}
    table = soup.find('table', class_='table-bordered')
    if not table: return timetable
    if table.thead and table.thead.tr:
        for th in table.thead.tr.find_all('th'):
            timetable["headers"].append(th.text.strip())
    if table.tbody:
        for row in table.tbody.find_all('tr'):
            timetable["rows"].append([' '.join(td.stripped_strings) or "---" for td in row.find_all('td')])
    return timetable

application = app

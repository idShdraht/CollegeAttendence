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
BROWSERLESS_API_KEY = "2T04KUPWyHqoQsb254cabf9969a21ff868ac5eb097bc906c9"
HF_API_KEY = "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"
# Debug will write preprocessed captcha to debug_captcha.png
DEFAULT_DEBUG = True
# ----------------------------

print("J.A.R.V.I.S. Sentinel Engine: Initializing...")

app = Flask(__name__)
app.secret_key = 'jarvis-secret-key-for-sentinel'
CORS(app, supports_credentials=True, origins=["*"])

@app.errorhandler(500)
def internal_server_error(e):
    traceback.print_exc()
    return jsonify(error="J.A.R.V.I.S. Core Systems Failure: A critical, unhandled error occurred."), 500

def get_remote_browser():
    """Connects to the Browserless.io remote fleet."""
    print("J.A.R.V.I.S. LOG: Connecting to Sentinel browser fleet...")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # optionally run headless if you prefer
    # options.add_argument("--headless=new")

    endpoint = f'wss://chrome.browserless.io?token={BROWSERLESS_API_KEY}'
    driver = webdriver.Remote(command_executor=endpoint, options=options)
    print("J.A.R.V.I.S. LOG: Connection established.")
    return driver

def preprocess_captcha(image_bytes, debug=DEFAULT_DEBUG):
    """
    Preprocess image bytes: grayscale -> Otsu threshold -> return processed PNG bytes.
    Also optionally save debug_captcha.png.
    """
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

    if debug:
        try:
            pil_img.save("debug_captcha.png")
            print("J.A.R.V.I.S. DEBUG: Preprocessed captcha saved as debug_captcha.png")
        except Exception:
            pass

    return processed_bytes

def solve_captcha_with_service(image_bytes, debug=DEFAULT_DEBUG):
    """
    Preprocess captcha, send to Hugging Face chat completions endpoint with strict prompt,
    and return only the text answer (trimmed).
    """
    print("J.A.R.V.I.S. LOG: Preprocessing captcha image...")
    processed_bytes = preprocess_captcha(image_bytes, debug=debug)

    image_b64 = base64.b64encode(processed_bytes).decode("utf-8")

    prompt = (
        "Solve the captcha in this image. "
        "Just tell the solution for the captcha, no other words, no explanation."
    )

    payload = {
        "inputs": {
            "messages": [
                {"role": "system", "content": "You are a captcha solver."},
                {"role": "user", "content": prompt},
                {"role": "user", "content": f"data:image/png;base64,{image_b64}"}
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    print("J.A.R.V.I.S. LOG: Sending captcha to LLM via Hugging Face inference...")
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()

        captcha_text = None
        if isinstance(result, dict):
            choices = result.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                msg = choices[0].get("message") or choices[0]
                if isinstance(msg, dict):
                    captcha_text = (msg.get("content") or msg.get("text") or "").strip()
                else:
                    captcha_text = str(msg).strip()
            else:
                captcha_text = (result.get("text") or "").strip()
        elif isinstance(result, list) and len(result) > 0:
            first = result[0]
            captcha_text = (first.get("generated_text") or first.get("text") or "").strip()

        if not captcha_text:
            raise RuntimeError(f"Could not parse LLM response for captcha. Full response: {result}")

        captcha_text = captcha_text.splitlines()[0].strip()
        print(f"J.A.R.V.I.S. LOG: Captcha solved as '{captcha_text}'")
        return captcha_text

    except Exception as e:
        print("J.A.R.V.I.S. ERROR: Failed to solve captcha with LLM.")
        traceback.print_exc()
        raise RuntimeError("Captcha solving with LLM failed.") from e

def js_set_value_and_dispatch(driver, element, value):
    """
    Set value of an element via JS and dispatch input events to mimic paste/typing behavior.
    """
    set_value_script = """
    (el, val) => {
        el.focus();
        el.value = val;
        const ev = new Event('input', { bubbles: true});
        el.dispatchEvent(ev);
        const ev2 = new Event('change', { bubbles: true});
        el.dispatchEvent(ev2);
    }
    """
    driver.execute_script(set_value_script, element, value)

@app.route('/api/scrape', methods=['POST'])
def scrape_data():
    """Main endpoint: receives rollNo and password, fills the site, solves captcha, logs in, scrapes."""
    driver = None
    try:
        payload = request.get_json(force=True)
        roll_no = payload.get('rollNo')
        password = payload.get('password')
        debug = payload.get('debug', DEFAULT_DEBUG)

        if not roll_no or not password:
            return jsonify({"error": "rollNo and password are required."}), 400

        driver = get_remote_browser()
        print(f"J.A.R.V.I.S. LOG: Beginning automated login for {roll_no}.")
        driver.get(f"{AIMS_BASE_URL}/student/loginPage")

        wait = WebDriverWait(driver, 20)

        student_no_el = wait.until(EC.presence_of_element_located((By.NAME, "studentNo")))
        password_el = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        captcha_el = wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'captcha')]")))
        submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']")))

        print("J.A.R.V.I.S. LOG: Pasting roll number and password into page fields.")
        js_set_value_and_dispatch(driver, student_no_el, roll_no)
        js_set_value_and_dispatch(driver, password_el, password)

        print("J.A.R.V.I.S. LOG: Capturing captcha image bytes.")
        image_bytes = captcha_el.screenshot_as_png

        captcha_solution = solve_captcha_with_service(image_bytes, debug=debug)
        if not captcha_solution:
            raise RuntimeError("LLM returned empty captcha solution.")

        captcha_input_el = driver.find_element(By.NAME, 'captcha')
        print(f"J.A.R.V.I.S. LOG: Pasting captcha solution '{captcha_solution}' into captcha input.")
        js_set_value_and_dispatch(driver, captcha_input_el, captcha_solution)

        print("J.A.R.V.I.S. LOG: Submitting the login form.")
        submit_btn.click()

        try:
            WebDriverWait(driver, 12).until(EC.url_contains("dashboard"))
        except Exception:
            time.sleep(3)

        print("J.A.R.V.I.S. LOG: Login attempt complete; extracting attendance and timetable.")
        driver.get(f"{AIMS_BASE_URL}/student/AttndReport")
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        attendance_html = driver.page_source

        driver.get(f"{AIMS_BASE_URL}/student/timetable")
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered")))
        timetable_html = driver.page_source

        full_data = {
            "attendanceData": parse_attendance_data(attendance_html, roll_no),
            "timetableData": parse_timetable_data(timetable_html)
        }
        return jsonify(full_data)

    except Exception as e:
        print("--- UNEXPECTED SENTINEL ENGINE ERROR ---")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred on the backend.", "detail": str(e)}), 500
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def parse_attendance_data(html_content, roll_no):
    soup = BeautifulSoup(html_content, 'html.parser')
    SUBJECT_COLUMN = 2; HELD_HOURS_COLUMN = 6; ATTENDED_HOURS_COLUMN = 7
    subjects = []; total_held_hours = 0; total_attended_hours = 0
    attendance_table = soup.find('table', class_='table-bordered')
    if not attendance_table: raise ValueError("Could not find attendance table.")
    tbody = attendance_table.find('tbody')
    if not tbody: raise ValueError("Attendance table malformed: missing tbody.")
    table_rows = tbody.find_all('tr')
    for row in table_rows:
        cols = row.find_all('td')
        if len(cols) > max(SUBJECT_COLUMN, HELD_HOURS_COLUMN, ATTENDED_HOURS_COLUMN):
            try:
                subject_name = cols[SUBJECT_COLUMN].text.strip()
                held = float(cols[HELD_HOURS_COLUMN].text.strip())
                attended = float(cols[ATTENDED_HOURS_COLUMN].text.strip())
                subjects.append({"name": subject_name, "held": held, "attended": attended})
                total_held_hours += held; total_attended_hours += attended
            except (ValueError, IndexError):
                continue
    overall_percentage = (total_attended_hours / total_held_hours) * 100 if total_held_hours > 0 else 0
    return { "rollNo": roll_no, "overallAttendance": round(overall_percentage, 2), "subjects": subjects }

def parse_timetable_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    timetable = {"headers": [], "rows": []}
    table = soup.find('table', class_='table-bordered')
    if not table: return timetable
    thead = table.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            for th in header_row.find_all('th'):
                timetable["headers"].append(th.text.strip())
    tbody = table.find('tbody')
    if not tbody:
        return timetable
    body_rows = tbody.find_all('tr')
    for row in body_rows:
        time_slot_data = []
        for td in row.find_all('td'):
            class_info = ' '.join(td.stripped_strings)
            time_slot_data.append(class_info if class_info else "---")
        timetable["rows"].append(time_slot_data)
    return timetable

if __name__ == "__main__":
    print("J.A.R.V.I.S. Sentinel Engine: All systems nominal. Engaging server.")
    app.run(host="0.0.0.0", port=5000, debug=False)














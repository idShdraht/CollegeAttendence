from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback

# ---------------- CONFIG ----------------
AIMS_BASE_URL = "https://aims.rkmvc.ac.in"
BROWSERLESS_API_KEY = os.environ.get("BROWSERLESS_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")
# ----------------------------------------

print("J.A.R.V.I.S. Sentinel Engine: Initializing...")

app = Flask(__name__)
app.secret_key = 'jarvis-secret-key-for-sentinel'

# --- CORS (only allow your frontend) ---
CORS(app, resources={
    r"/api/*": {"origins": "https://starkattend.netlify.app"}
})

@app.errorhandler(500)
def internal_server_error(e):
    traceback.print_exc()
    return jsonify(error="J.A.R.V.I.S. Core Systems Failure: A critical, unhandled error occurred."), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "J.A.R.V.I.S. Engine is running 🚀", "status": "online"})

@app.route("/api/scrape", methods=["POST"])
def scrape_data():
    try:
        data = request.get_json()
        roll_no = data.get("rollNo")
        password = data.get("password")

        if not roll_no or not password:
            return jsonify({"error": "Missing rollNo or password"}), 400

        # ✅ Dummy attendance + timetable (replace with Selenium scraping later)
        attendance_data = [
            {"subject": "Python Programming", "percentage": 92},
            {"subject": "Advanced Accounts", "percentage": 84},
            {"subject": "Corporate Law", "percentage": 75},
        ]
        timetable_data = [
            {"day": "Monday", "subject": "Python Programming", "time": "9:00 AM"},
            {"day": "Wednesday", "subject": "Advanced Accounts", "time": "10:30 AM"},
            {"day": "Friday", "subject": "Corporate Law", "time": "11:00 AM"},
        ]

        return jsonify({
            "message": "Scraping successful ✅",
            "attendanceData": attendance_data,
            "timetableData": timetable_data
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

































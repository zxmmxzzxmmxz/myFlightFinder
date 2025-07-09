from flask import Flask, render_template_string, request
import requests
import threading
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

app = Flask(__name__)

GMAIL_USER = "GMAIL EMAIL Address"
GMAIL_PASS = "YOUR GMAIL CODE"
TO_EMAIL = "Email"

CHECK_DATES = ["20250601", "20250602", "20250603"]  # Hardcoded target dates for alert
LAST_ALERTED = set()

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Available Flights Table</title>
  <style>
    table {
      border-collapse: collapse;
      width: 100%;
      font-family: Arial, sans-serif;
    }
    th, td {
      border: 1px solid #ccc;
      padding: 8px 12px;
      text-align: center;
    }
    th {
      background-color: #f2f2f2;
    }
    .H { background-color: #c8e6c9; }
    .L { background-color: #ffe0b2; }
  </style>
</head>
<body>
  <h2>{{ from_airport }} → {{ to_airport }} {{fare_class}} Class - Available Dates</h2>
  <table>
    <tr>
      <th>Date</th>
      <th>Availability</th>
    </tr>
    {% for row in rows %}
    <tr>
      <td>{{ row.date }}</td>
      <td class="{{ row.availability }}">{{ row.availability }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

def format_date(raw_date):
    return datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")

def send_email_alert(date, status):
    msg = MIMEText(f"✅ Flight available on {format_date(date)} — Status: {status}")
    msg['Subject'] = f"Flight Alert: {date} is {status}"
    msg['From'] = GMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print(f"[EMAIL SENT] {date} is {status}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")

def send_email_startup():
    msg = MIMEText("🛫 Flight Availability Monitor has started.\n\nDates being watched:\n- June 1\n- June 2\n- June 3")
    msg['Subject'] = "Flight Monitor Started"
    msg['From'] = GMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print("[EMAIL SENT] Startup notification")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send startup email: {e}")

def build_api_url(from_code, to_code, fare_class):
    today = datetime.today()
    end = today + timedelta(days=180)
    start_date = today.strftime("%Y%m%d")
    end_date = end.strftime("%Y%m%d")
    return f"https://api.cathaypacific.com/afr/search/availability/en.{from_code}.{to_code}.{fare_class}.CX.1.{start_date}.{end_date}.json"

def monitor_availability():
    global LAST_ALERTED
    send_email_startup()

    # Hardcoded for alert check; if you want to make this dynamic too, let me know.
    api_url = build_api_url("HKG", "YVR", "bus")

    while True:
        try:
            response = requests.get(api_url)
            std = response.json()["availabilities"]["std"]

            for entry in std:
                date = entry["date"]
                status = entry["availability"]
                if date in CHECK_DATES and status in ("H", "L") and date not in LAST_ALERTED:
                    send_email_alert(date, status)
                    LAST_ALERTED.add(date)

        except Exception as e:
            print(f"[ERROR] Failed to check availability: {e}")

        time.sleep(3600)

@app.route("/")
def show_table():
    from_code = request.args.get("from", "HKG")
    to_code = request.args.get("to", "YVR")
    fare_class = request.args.get("class", "bus")

    api_url = build_api_url(from_code, to_code, fare_class)
    response = requests.get(api_url)
    std = response.json()["availabilities"]["std"]

    rows = [
        {
            "date": format_date(entry["date"]),
            "availability": entry["availability"]
        }
        for entry in std if entry["availability"] != "NA"
    ]

    return render_template_string(TEMPLATE, rows=rows, from_airport=from_code, to_airport=to_code)

if __name__ == "__main__":
    thread = threading.Thread(target=monitor_availability, daemon=True)
    thread.start()
    app.run(host="0.0.0.0")

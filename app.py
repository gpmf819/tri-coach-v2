import os
import requests
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY")
API_SECRET = os.environ.get("API_SECRET")
ATHLETE_ID = "i169728"
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
TZ = pytz.timezone("America/Montreal")

def now_local():
    return datetime.now(TZ)

def check_auth():
    token = request.headers.get("X-API-Key")
    if token != API_SECRET:
        return False
    return True

def intervals_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        auth=("API_KEY", INTERVALS_API_KEY),
        params=params
    )
    response.raise_for_status()
    return response.json()

@app.route("/athlete")
def athlete():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = intervals_get("")
    return jsonify({
        "id": data.get("id"),
        "name": data.get("name"),
        "ftp": data.get("sportSettings", [{}])[0].get("ftp"),
        "lthr": data.get("sportSettings", [{}])[0].get("lthr"),
        "max_hr": data.get("sportSettings", [{}])[0].get("max_hr"),
        "resting_hr": data.get("icu_resting_hr"),
        "weight": data.get("icu_weight"),
        "timezone": data.get("timezone")
    })

@app.route("/wellness")
def wellness():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    today = now_local().strftime("%Y-%m-%d")
    data = intervals_get("/wellness", params={"oldest": today, "newest": today})
    return jsonify(data)

@app.route("/activities")
def activities():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    days = int(request.args.get("days", 7))
    oldest = (now_local() - timedelta(days=days)).strftime("%Y-%m-%d")
    today = now_local().strftime("%Y-%m-%d")
    data = intervals_get("/activities", params={"oldest": oldest, "newest": today})
    return jsonify(data)

@app.route("/calendar")
def calendar():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    today = now_local().strftime("%Y-%m-%d")
    two_weeks = (now_local() + timedelta(weeks=2)).strftime("%Y-%m-%d")
    data = intervals_get("/events", params={"oldest": today, "newest": two_weeks})
    return jsonify(data)

if __name__ == "__main__":
    app.run()

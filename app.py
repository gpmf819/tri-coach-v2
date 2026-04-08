import os
import requests
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import pytz
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

@app.route("/snapshot")
def snapshot():
    today = now_local().strftime("%Y-%m-%d")
    day_of_week = now_local().strftime("%A")
    two_weeks = (now_local() + timedelta(weeks=2)).strftime("%Y-%m-%d")

    wellness_data = intervals_get("/wellness", params={"oldest": today, "newest": today})
    w = wellness_data[0] if isinstance(wellness_data, list) and wellness_data else {}
    ctl = round(w.get("ctl", 0), 1)
    atl = round(w.get("atl", 0), 1)
    tsb = round(ctl - atl, 1)
    ramp = round(w.get("rampRate", 0), 1)

    activities_data = intervals_get("/activities", params={
        "oldest": (now_local() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "newest": today
    })
    activities = []
    for a in (activities_data or [])[:4]:
        secs = a.get("moving_time", 0)
        h, m = divmod(secs // 60, 60)
        dur = f"{h}h{m}m" if h else f"{m}m"
        rpe = a.get("icu_rpe") or "-"
        feel = a.get("feel") or "-"
        activities.append(f"  - {a.get('start_date_local','')[:10]} {a.get('type','')} \"{a.get('name','')}\" {dur} load:{a.get('icu_training_load','?')} RPE:{rpe} feel:{feel}")

    calendar_data = intervals_get("/events", params={"oldest": today, "newest": two_weeks})
    planned = []
    for e in (calendar_data or [])[:4]:
        planned.append(f"  - {e.get('start_date_local','')[:10]} {e.get('type','')} \"{e.get('name','')}\"")

    snapshot_text = f"""=== COACH DATA SNAPSHOT ===
Date: {today} ({day_of_week})

LOAD
  CTL: {ctl} | ATL: {atl} | TSB: {tsb} | Ramp: +{ramp}/week

RECENT ACTIVITIES (last 7 days)
{chr(10).join(activities) or '  none'}

UPCOMING PLANNED
{chr(10).join(planned) or '  none'}
==========================="""

    return snapshot_text, 200, {"Content-Type": "text/plain"}

@app.route("/runpaces")
def runpaces():
    today = now_local().strftime("%Y-%m-%d")
    oldest = (now_local() - timedelta(days=90)).strftime("%Y-%m-%d")
    data = intervals_get("/activities", params={"oldest": oldest, "newest": today})

    runs = [a for a in (data or []) if a.get("type") in ["Run", "VirtualRun"]]

    result = []
    for r in runs[:10]:
        secs = r.get("moving_time", 0)
        h, m = divmod(secs // 60, 60)
        dur = f"{h}h{m}m" if h else f"{m}m"
        dist = round((r.get("distance", 0) or 0) / 1000, 2)
        pace_ms = r.get("pace", 0) or 0
        pace_min = int(pace_ms // 60) if pace_ms else 0
        pace_sec = int(pace_ms % 60) if pace_ms else 0
        avg_hr = r.get("average_heartrate") or "-"
        result.append(
            f"{r.get('start_date_local','')[:10]} \"{r.get('name','')}\" "
            f"{dist}km {dur} pace:{pace_min}:{pace_sec:02d}/km HR:{avg_hr} "
            f"load:{r.get('icu_training_load','?')}"
        )

    return "\n".join(result), 200, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    app.run()

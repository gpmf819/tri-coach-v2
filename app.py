import os
import requests
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from urllib.parse import quote
import pytz
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY")
API_SECRET = os.environ.get("API_SECRET")
ATHLETE_ID = "i169728"
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
TZ = pytz.timezone("America/Montreal")

WORKOUT_LIBRARY = {
    # NOR Bike
    "NOR_Bike_MidWeek_4x8": {"type": "Ride", "moving_time": 4800},
    "NOR_Bike_OverUnder_3x12": {"type": "Ride", "moving_time": 5160},
    "NOR_Bike_RaceSim_Olympic": {"type": "Ride", "moving_time": 5160},
    "NOR_Bike_SweetSpot_2x20": {"type": "Ride", "moving_time": 5400},
    "NOR_Bike_SweetSpot_3x15": {"type": "Ride", "moving_time": 5940},
    "NOR_Bike_ThresholdProgression_3x15": {"type": "Ride", "moving_time": 5940},
    "NOR_Bike_VO2max_4x4": {"type": "Ride", "moving_time": 4200},
    "NOR_Bike_VO2max_30_30": {"type": "Ride", "moving_time": 4200},
    "NOR_Brick_BikeRun": {"type": "Ride", "moving_time": 5400},
    "NOR_Bike_LowCadence_MuscTension": {"type": "Ride", "moving_time": 4260},
    "NOR_Bike_Main_5x10": {"type": "Ride", "moving_time": 6030},
    # NOR Run
    "NOR_Run_5x6_Threshold": {"type": "Run", "moving_time": 4200},
    "NOR_Run_Brick_OffBike": {"type": "Run", "moving_time": 1800},
    "NOR_Run_Easy_Zone1": {"type": "Run", "moving_time": 2600},
    "NOR_Run_Long_NegativeSplit": {"type": "Run", "moving_time": 4800},
    "NOR_Run_PreRace_Opener": {"type": "Run", "moving_time": 1500},
    "NOR_Run_RacePace_5x8": {"type": "Run", "moving_time": 5400},
    "NOR_Run_Strides_Neuromuscular": {"type": "Run", "moving_time": 2700},
    "NOR_Run_Tempo_3x12": {"type": "Run", "moving_time": 4440},
    "NOR_Run_VO2max_7x3": {"type": "Run", "moving_time": 4800},
    # NOR Swim
    "NOR_Swim_EasyAerobic_30min": {"type": "Swim", "moving_time": 1800},
    "NOR_Swim_CSS_Threshold_30min": {"type": "Swim", "moving_time": 1320},
    "NOR_Swim_Speed_45min": {"type": "Swim", "moving_time": 2010},
    "NOR_Swim_RaceSim_45min": {"type": "Swim", "moving_time": 2550},
    # PAM Series
    "PAM00 z-5": {"type": "Ride", "moving_time": 2205},
    "PAM01 z-5": {"type": "Ride", "moving_time": 3105},
    "PAM02 z-5": {"type": "Ride", "moving_time": 2970},
    "PAM03 z-5": {"type": "Ride", "moving_time": 2175},
    "PAM05 z-5": {"type": "Ride", "moving_time": 2715},
    "PAM06 z-5": {"type": "Ride", "moving_time": 3330},
    "PAM07 z-5": {"type": "Ride", "moving_time": 2475},
    # FTK Series
    "FTK-13": {"type": "Ride", "moving_time": 1560},
    "FTK-14": {"type": "Ride", "moving_time": 1590},
    # Gimenez
    "Gimenez_01": {"type": "Ride", "moving_time": 3420},
    "Gimenez_02": {"type": "Ride", "moving_time": 3420},
    # Pacing
    "PACING Prog #01": {"type": "Ride", "moving_time": 1790},
    # Power Cycling Enduro
    "Power Cycling Enduro #02": {"type": "Ride", "moving_time": 4080},
    "Power Cycling Enduro #03": {"type": "Ride", "moving_time": 4220},
    "Power Cycling Enduro #04": {"type": "Ride", "moving_time": 4185},
    # Tempo Series
    "Tempo#00": {"type": "Ride", "moving_time": 1710},
    "Tempo#01": {"type": "Ride", "moving_time": 2610},
    "Tempo#02": {"type": "Ride", "moving_time": 2550},
    "Tempo#05": {"type": "Ride", "moving_time": 3870},
    "Tempo#08": {"type": "Ride", "moving_time": 2535},
    "Tempo_Force": {"type": "Ride", "moving_time": 3080},
}

def now_local():
    return datetime.now(TZ)

def check_auth():
    token = request.headers.get("X-API-Key")
    return token == API_SECRET

def intervals_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        auth=("API_KEY", INTERVALS_API_KEY),
        params=params
    )
    response.raise_for_status()
    return response.json()

def intervals_post(path, payload):
    response = requests.post(
        f"{BASE_URL}{path}",
        auth=("API_KEY", INTERVALS_API_KEY),
        json=payload
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
        if pace_ms and pace_ms > 0:
            secs_per_km = 1000 / pace_ms
            pace_min = int(secs_per_km // 60)
            pace_sec = int(secs_per_km % 60)
        else:
            pace_min, pace_sec = 0, 0
        avg_hr = r.get("average_heartrate") or "-"
        result.append(
            f"{r.get('start_date_local','')[:10]} \"{r.get('name','')}\" "
            f"{dist}km {dur} pace:{pace_min}:{pace_sec:02d}/km HR:{avg_hr} "
            f"load:{r.get('icu_training_load','?')}"
        )

    return "\n".join(result), 200, {"Content-Type": "text/plain"}

@app.route("/workouts")
def workouts():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = intervals_get("/workouts")
    return jsonify([{"id": w.get("id"), "name": w.get("name"), "type": w.get("type")} for w in (data or [])])

@app.route("/schedule", methods=["POST"])
def schedule():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "workouts" not in data:
        return jsonify({"error": "Missing workouts array"}), 400

    results = []
    errors = []

    for item in data["workouts"]:
        name = item.get("name", "").strip()
        date = item.get("date", "").strip()

        if not name or not date:
            errors.append({"name": name, "error": "Missing name or date"})
            continue

        workout_meta = WORKOUT_LIBRARY.get(name)
        if not workout_meta:
            errors.append({"name": name, "error": "Workout not found in library"})
            continue

        try:
            zwo_filename = f"{name}.zwo"
            zwo_url = f"https://raw.githubusercontent.com/gpmf819/tri-coach-v2/main/workouts/{quote(zwo_filename)}"
            zwo_response = requests.get(zwo_url)

            if zwo_response.status_code == 200:
                payload = {
                    "category": "WORKOUT",
                    "start_date_local": f"{date}T00:00:00",
                    "type": workout_meta["type"],
                    "filename": zwo_filename,
                    "file_contents": zwo_response.text
                }
            else:
                payload = {
                    "category": "WORKOUT",
                    "start_date_local": f"{date}T00:00:00",
                    "type": workout_meta["type"],
                    "name": name,
                    "moving_time": workout_meta["moving_time"]
                }

            result = intervals_post("/events", payload)
            results.append({"name": name, "date": date, "id": result.get("id"), "status": "scheduled"})

        except Exception as e:
            errors.append({"name": name, "date": date, "error": str(e)})

    return jsonify({"scheduled": results, "errors": errors})

if __name__ == "__main__":
    app.run()

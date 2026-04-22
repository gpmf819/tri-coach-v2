import os
import requests
from flask import Flask, jsonify, request, Response, stream_with_context
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY")
API_SECRET = os.environ.get("API_SECRET")
ANTHROPIC_API_KEY = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
ATHLETE_ID = "i169728"
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
TZ = pytz.timezone("America/Montreal")

# --- CORS ---

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return "", 200

# --- Helpers ---

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

# --- Existing endpoints ---

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

@app.route("/workouts/names")
def workout_names():
    data = intervals_get("/workouts")
    by_type = {}
    for w in (data or []):
        t = w.get("type", "Other")
        by_type.setdefault(t, []).append(w.get("name", ""))
    lines = ["Available workouts by type:"]
    for t, names in sorted(by_type.items()):
        lines.append(f"\n{t}:")
        for n in sorted(names):
            lines.append(f"  - {n}")
    return "\n".join(lines), 200, {"Content-Type": "text/plain"}

@app.route("/workouts/<int:workout_id>")
def workout_detail(workout_id):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(intervals_get(f"/workouts/{workout_id}"))

@app.route("/schedule", methods=["POST"])
def schedule():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "workouts" not in data:
        return jsonify({"error": "Missing workouts array"}), 400

    results = []
    errors = []

    # Build name→id map once if any item uses name instead of workout_id
    items = data["workouts"]
    needs_name_lookup = any(item.get("name") and not item.get("workout_id") for item in items)
    name_to_id = {}
    name_to_id_norm = {}
    if needs_name_lookup:
        try:
            all_workouts = intervals_get("/workouts")
            name_to_id = {w["name"]: w["id"] for w in (all_workouts or []) if w.get("name") and w.get("id")}
            # Normalized fallback: case-insensitive, underscores↔spaces
            name_to_id_norm = {k.lower().replace("_", " "): v for k, v in name_to_id.items()}
        except Exception as e:
            return jsonify({"error": f"Failed to fetch workout library: {e}"}), 502

    for item in items:
        workout_id = item.get("workout_id")
        name = item.get("name", "").strip()
        date = item.get("date", "").strip()

        if not workout_id and name:
            workout_id = name_to_id.get(name) or name_to_id_norm.get(name.lower().replace("_", " "))
            if not workout_id:
                errors.append({
                    "name": name,
                    "date": date,
                    "error": f"Workout '{name}' not found in library",
                    "available": sorted(name_to_id.keys())
                })
                continue

        if not workout_id or not date:
            errors.append({"workout_id": workout_id, "error": "Missing workout_id (or name) and date"})
            continue

        try:
            workout = intervals_get(f"/workouts/{workout_id}")
            payload = {
                "category": "WORKOUT",
                "start_date_local": f"{date}T00:00:00",
                "type": workout["type"],
                "name": workout["name"],
                "moving_time": workout["moving_time"],
                "description": workout["description"],
            }
            result = intervals_post("/events", payload)
            results.append({
                "workout_id": workout_id,
                "name": workout["name"],
                "date": date,
                "id": result.get("id"),
                "status": "scheduled",
            })

        except Exception as e:
            errors.append({"workout_id": workout_id, "date": date, "error": str(e)})

    return jsonify({"scheduled": results, "errors": errors})

# --- Anthropic proxy ---

@app.route("/chat", methods=["POST"])
def chat():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500

    body = request.get_json()
    if not body:
        return jsonify({"error": "Missing request body"}), 400

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    stream = body.get("stream", False)

    upstream = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=body,
        stream=stream,
    )

    if stream:
        def generate():
            for chunk in upstream.iter_content(chunk_size=None):
                yield chunk
        return Response(
            stream_with_context(generate()),
            status=upstream.status_code,
            content_type="text/event-stream",
        )

    return Response(
        upstream.content,
        status=upstream.status_code,
        content_type="application/json",
    )

if __name__ == "__main__":
    app.run()

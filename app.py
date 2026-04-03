import os
import requests
from flask import Flask, jsonify, request
from datetime import datetime, timedelta

app = Flask(__name__)

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY")
ATHLETE_ID = os.environ.get("ATHLETE_ID", "i169728")
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"

def intervals_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        auth=("API_KEY", INTERVALS_API_KEY),
        params=params
    )
    response.raise_for_status()
    return response.json()

@app.route("/wellness")
def wellness():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = intervals_get("/wellness", params={"oldest": today, "newest": today})
    return jsonify(data)

@app.route("/activities")
def activities():
    days = int(request.args.get("days", 7))
    oldest = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    data = intervals_get("/activities", params={"oldest": oldest})
    return jsonify(data)

@app.route("/calendar")
def calendar():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    two_weeks = (datetime.utcnow() + timedelta(weeks=2)).strftime("%Y-%m-%d")
    data = intervals_get("/events", params={"oldest": today, "newest": two_weeks})
    return jsonify(data)

@app.route("/athlete")
def athlete():
    data = intervals_get("")
    return jsonify(data)

if __name__ == "__main__":
    app.run()

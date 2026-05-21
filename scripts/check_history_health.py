import json
from datetime import date
from pathlib import Path

today = date.today().isoformat()

latest_file = Path("data/latest.json")
today_snapshot = Path(f"history/daily/{today}.json")
trends_file = Path("data/trends-30d.json")
status_file = Path("data/history-status.json")

errors = []
warnings = []

def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

if not latest_file.exists():
    errors.append("data/latest.json is missing.")

if not today_snapshot.exists():
    errors.append(f"Today snapshot is missing: {today_snapshot}")

if not trends_file.exists():
    errors.append("data/trends-30d.json is missing.")

station_count = 0
days_available = 0

if today_snapshot.exists():
    snapshot = read_json(today_snapshot)
    station_count = snapshot.get("station_count", 0)

    if station_count <= 0:
        errors.append("Today snapshot has zero stations.")

if trends_file.exists():
    trends = read_json(trends_file)
    days_available = trends.get("days_available", 0)

    if days_available <= 0:
        errors.append("Trend analysis has zero days available.")

    averages = trends.get("uk_average", {})
    if not averages:
        warnings.append("No fuel averages found in trends file.")

status = {
    "status": "failed" if errors else "success",
    "last_checked_date": today,
    "today_snapshot": str(today_snapshot),
    "station_count": station_count,
    "days_available": days_available,
    "errors": errors,
    "warnings": warnings
}

status_file.parent.mkdir(parents=True, exist_ok=True)

with status_file.open("w", encoding="utf-8") as f:
    json.dump(status, f, ensure_ascii=False, indent=2)

if errors:
    print("Health check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Health check passed.")

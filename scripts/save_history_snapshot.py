import json
from datetime import date
from pathlib import Path

DATA_FILE = Path("data/latest.json")
HISTORY_DIR = Path("history/daily")

today = date.today().isoformat()
snapshot_file = HISTORY_DIR / f"{today}.json"

HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if not DATA_FILE.exists():
    raise FileNotFoundError("data/latest.json not found.")

if snapshot_file.exists():
    print(f"Snapshot already exists for {today}. Skipping.")
    exit(0)

with DATA_FILE.open("r", encoding="utf-8") as f:
    latest_data = json.load(f)

stations = latest_data.get("stations", [])

snapshot = {
    "snapshot_date": today,
    "source": latest_data.get("source", "Driverz latest fuel data"),
    "station_count": latest_data.get("station_count", len(stations)),
    "stations": stations
}

with snapshot_file.open("w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))

print(f"Saved snapshot: {snapshot_file}")

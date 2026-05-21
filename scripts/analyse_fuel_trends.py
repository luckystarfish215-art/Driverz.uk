import json
from glob import glob
from pathlib import Path
from statistics import mean

HISTORY_FILES = sorted(glob("history/daily/*.json"))[-30:]
OUTPUT_FILE = Path("data/trends-30d.json")

FUEL_TYPES = ["e5", "e10", "b7", "sdv"]

def get_avg(snapshot, fuel):
    prices = []

    for station in snapshot.get("stations", []):
        value = station.get(fuel)

        if isinstance(value, (int, float)):
            prices.append(value)

    return round(mean(prices), 2) if prices else None

if not HISTORY_FILES:
    print("No history files found. Skipping trend analysis.")
    exit(0)

snapshots = []

for file in HISTORY_FILES:
    with open(file, "r", encoding="utf-8") as f:
        snapshots.append(json.load(f))

latest = snapshots[-1]
oldest = snapshots[0]

summary = {
    "generated_at": latest.get("snapshot_date"),
    "days_available": len(snapshots),
    "uk_average": {}
}

for fuel in FUEL_TYPES:
    today_avg = get_avg(latest, fuel)
    old_avg = get_avg(oldest, fuel)

    summary["uk_average"][fuel] = {
        "today": today_avg,
        "previous": old_avg,
        "change": round(today_avg - old_avg, 2)
        if today_avg is not None and old_avg is not None
        else None
    }

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Generated {OUTPUT_FILE}")

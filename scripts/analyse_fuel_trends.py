import json
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from statistics import mean

HISTORY_FILES = sorted(glob("history/daily/*.json"))[-30:]
OUTPUT_FILE = Path("data/trends-30d.json")
STATUS_FILE = Path("data/trends-status.json")

FUEL_TYPES = ["e5", "e10", "b7", "sdv"]
MIN_PRICE = 80
MAX_PRICE = 300
MIN_STATIONS_WITH_PRICE = 100


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_snapshot(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return None, f"invalid_json: {exc}"

    stations = data.get("stations", [])
    if not isinstance(stations, list) or not stations:
        return None, "missing_or_empty_stations"

    snapshot_date = data.get("snapshot_date") or Path(path).stem

    return {
        "file": str(path),
        "snapshot_date": snapshot_date,
        "stations": stations,
        "station_count": len(stations),
    }, None


def price_values(snapshot, fuel):
    values = []

    for station in snapshot.get("stations", []):
        value = station.get(fuel)

        if isinstance(value, (int, float)) and MIN_PRICE <= value <= MAX_PRICE:
            values.append(float(value))

    return values


def fuel_average(snapshot, fuel):
    values = price_values(snapshot, fuel)

    if len(values) < MIN_STATIONS_WITH_PRICE:
        return None, len(values)

    return round(mean(values), 2), len(values)


loaded_snapshots = []
skipped_files = []

for file in HISTORY_FILES:
    snapshot, error = load_snapshot(file)

    if error:
        skipped_files.append({"file": str(file), "reason": error})
        continue

    loaded_snapshots.append(snapshot)

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "latest_snapshot_date": None,
    "days_available": len(HISTORY_FILES),
    "valid_snapshot_days": 0,
    "skipped_snapshot_days": len(skipped_files),
    "uk_average": {},
}

if not loaded_snapshots:
    summary["message"] = "No readable history snapshots found."
    write_json(OUTPUT_FILE, summary)
    write_json(STATUS_FILE, {"status": "failed", "message": summary["message"], "skipped_files": skipped_files})
    print(f"No readable history snapshots found. Generated {OUTPUT_FILE} with no averages.")
    raise SystemExit(0)

latest = loaded_snapshots[-1]
summary["latest_snapshot_date"] = latest["snapshot_date"]

valid_snapshot_dates = set()

for fuel in FUEL_TYPES:
    valid_for_fuel = []

    for snapshot in loaded_snapshots:
        avg, count = fuel_average(snapshot, fuel)

        if avg is not None:
            valid_for_fuel.append({
                "snapshot_date": snapshot["snapshot_date"],
                "average": avg,
                "station_count": snapshot["station_count"],
                "priced_station_count": count,
            })
            valid_snapshot_dates.add(snapshot["snapshot_date"])

    latest_entry = valid_for_fuel[-1] if valid_for_fuel else None
    previous_entry = valid_for_fuel[0] if len(valid_for_fuel) >= 2 else None

    today_avg = latest_entry["average"] if latest_entry else None
    previous_avg = previous_entry["average"] if previous_entry else None

    summary["uk_average"][fuel] = {
        "today": today_avg,
        "previous": previous_avg,
        "change": round(today_avg - previous_avg, 2) if today_avg is not None and previous_avg is not None else None,
        "today_snapshot_date": latest_entry["snapshot_date"] if latest_entry else None,
        "previous_snapshot_date": previous_entry["snapshot_date"] if previous_entry else None,
        "valid_days_for_fuel": len(valid_for_fuel),
        "priced_station_count": latest_entry["priced_station_count"] if latest_entry else 0,
    }

summary["valid_snapshot_days"] = len(valid_snapshot_dates)
summary["skipped_snapshot_days"] = len(HISTORY_FILES) - len(loaded_snapshots)

status = {
    "status": "success",
    "message": "Fuel trend analysis generated. Invalid or price-empty snapshots are ignored per fuel type.",
    "generated_at": summary["generated_at"],
    "history_files_checked": len(HISTORY_FILES),
    "readable_snapshot_days": len(loaded_snapshots),
    "valid_snapshot_days": summary["valid_snapshot_days"],
    "skipped_files": skipped_files,
}

write_json(OUTPUT_FILE, summary)
write_json(STATUS_FILE, status)

print(f"Generated {OUTPUT_FILE}")
print(f"Readable snapshots: {len(loaded_snapshots)} / {len(HISTORY_FILES)}")
print(f"Valid snapshot days used: {summary['valid_snapshot_days']}")

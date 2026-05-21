import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

CSV_FILE = Path("data/fuel_data.csv")

DATA_DIR = Path("data")
LATEST_FILE = DATA_DIR / "latest.json"
STATUS_FILE = DATA_DIR / "latest-status.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def normalise_key(key):
    return "".join(
        str(key)
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(".", "")
        .replace(" ", "")
        .split()
    )

def pick(row, aliases, default=None):
    normalised = {normalise_key(k): v for k, v in row.items()}

    for alias in aliases:
        value = normalised.get(normalise_key(alias))
        if value not in (None, ""):
            return value

    return default

def to_float(value):
    if value in (None, ""):
        return None

    try:
        return float(str(value).strip())
    except ValueError:
        return None

def to_price(value):
    price = to_float(value)

    if price is None:
        return None

    return round(price, 2)

def write_status(status, message, row_count=0, station_count=0, columns=None):
    payload = {
        "status": status,
        "message": message,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "csv_file": str(CSV_FILE),
        "row_count": row_count,
        "station_count": station_count,
        "columns": columns or []
    }

    STATUS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

if not CSV_FILE.exists():
    write_status("failed", f"CSV file not found: {CSV_FILE}")
    raise FileNotFoundError(f"CSV file not found: {CSV_FILE}")

raw = CSV_FILE.read_bytes()

try:
    text = raw.decode("utf-8-sig")
except UnicodeDecodeError:
    text = raw.decode("latin-1")

reader = csv.DictReader(io.StringIO(text))
rows = list(reader)

if not rows:
    write_status("failed", "CSV file exists but contains no rows.")
    raise SystemExit("CSV file exists but contains no rows.")

columns = reader.fieldnames or []
stations = []

for index, row in enumerate(rows, start=1):
    station_id = pick(row, [
        "site_id",
        "siteid",
        "site id",
        "id",
        "station_id",
        "station id",
        "Site ID"
    ], default=str(index))

    station = {
        "id": str(station_id),
        "brand": pick(row, ["brand", "Brand", "operator", "company"], ""),
        "name": pick(row, ["name", "site_name", "sitename", "site name", "station_name"], ""),
        "address": pick(row, ["address", "site_address", "site address"], ""),
        "postcode": pick(row, ["postcode", "post_code", "post code"], ""),
        "lat": to_float(pick(row, ["latitude", "lat"])),
        "lng": to_float(pick(row, ["longitude", "lng", "lon"])),
        "e5": to_price(pick(row, ["e5", "E5", "unleaded", "super unleaded"])),
        "e10": to_price(pick(row, ["e10", "E10", "petrol"])),
        "b7": to_price(pick(row, ["b7", "B7", "diesel"])),
        "sdv": to_price(pick(row, ["sdv", "SDV", "super diesel", "premium diesel"]))
    }

    stations.append(station)

output = {
    "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source": "data/fuel_data.csv",
    "station_count": len(stations),
    "stations": stations
}

LATEST_FILE.write_text(
    json.dumps(output, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

write_status(
    "success",
    "latest.json generated successfully from data/fuel_data.csv.",
    row_count=len(rows),
    station_count=len(stations),
    columns=columns
)

print(f"Generated {LATEST_FILE} with {len(stations)} stations.")

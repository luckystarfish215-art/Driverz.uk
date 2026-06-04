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

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# GOV.UK Fuel Finder CSV currently uses nested column names such as:
# forecourts.trading_name, forecourts.brand_name,
# forecourts.location.latitude, forecourts.fuel_price.E10, etc.
# This script also keeps older/simple aliases so it does not break if a
# downloaded CSV uses a slightly different naming style in future.


def normalise_key(key):
    return "".join(
        str(key or "")
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


def pick_bool(row, aliases):
    value = pick(row, aliases)
    if value in (None, ""):
        return None
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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

    # Fuel Finder prices are pence per litre. Reject impossible values so a
    # bad CSV row does not poison latest.json/history snapshots.
    if price < 80 or price > 300:
        return None

    return round(price, 1)


def compact_address(*parts):
    clean = []
    seen = set()
    for part in parts:
        text = str(part or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        clean.append(text)
        seen.add(key)
    return ", ".join(clean)


def opening_hours_from_row(row):
    usual_days = {}

    for day in DAYS:
        open_time = pick(row, [f"forecourts.opening_times.usual_days.{day}.open_time", f"opening_times.usual_days.{day}.open_time", f"{day}.open_time", f"{day}_open_time"], "")
        close_time = pick(row, [f"forecourts.opening_times.usual_days.{day}.close_time", f"opening_times.usual_days.{day}.close_time", f"{day}.close_time", f"{day}_close_time"], "")
        is_24_hours = pick_bool(row, [f"forecourts.opening_times.usual_days.{day}.is_24_hours", f"opening_times.usual_days.{day}.is_24_hours", f"{day}.is_24_hours", f"{day}_is_24_hours"])

        if open_time or close_time or is_24_hours is not None:
            usual_days[day] = {
                "open_time": str(open_time or "").strip(),
                "close_time": str(close_time or "").strip(),
                "is_24_hours": bool(is_24_hours),
            }

    bank_open = pick(row, ["forecourts.opening_times.bank_holiday.standard.open_time", "opening_times.bank_holiday.standard.open_time"], "")
    bank_close = pick(row, ["forecourts.opening_times.bank_holiday.standard.close_time", "opening_times.bank_holiday.standard.close_time"], "")
    bank_24 = pick_bool(row, ["forecourts.opening_times.bank_holiday.standard.is_24_hours", "opening_times.bank_holiday.standard.is_24_hours"])

    result = {"usual_days": usual_days}
    if bank_open or bank_close or bank_24 is not None:
        result["bank_holiday"] = {
            "standard": {
                "open_time": str(bank_open or "").strip(),
                "close_time": str(bank_close or "").strip(),
                "is_24_hours": bool(bank_24),
            }
        }

    return result if usual_days or "bank_holiday" in result else None


def format_opening_today(opening_hours):
    if not opening_hours:
        return ""

    today = datetime.now(timezone.utc).strftime("%A").lower()
    day = (opening_hours.get("usual_days") or {}).get(today) or {}

    if day.get("is_24_hours"):
        return "Open 24 hours"

    open_time = str(day.get("open_time") or "").strip()
    close_time = str(day.get("close_time") or "").strip()

    if open_time and close_time:
        return f"{open_time}–{close_time}"

    return ""


def write_json(path, payload, *, compact=False):
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
        ),
        encoding="utf-8",
    )


def write_status(status, message, row_count=0, station_count=0, usable_station_count=0, columns=None):
    payload = {
        "status": status,
        "message": message,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "csv_file": str(CSV_FILE),
        "row_count": row_count,
        "station_count": station_count,
        "usable_station_count": usable_station_count,
        "columns": columns or [],
    }
    write_json(STATUS_FILE, payload)


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
columns = reader.fieldnames or []

if not rows:
    write_status("failed", "CSV file exists but contains no rows.", columns=columns)
    raise SystemExit("CSV file exists but contains no rows.")

stations = []
usable_station_count = 0

for index, row in enumerate(rows, start=1):
    station_id = pick(
        row,
        [
            "forecourts.node_id",
            "node_id",
            "site_id",
            "siteid",
            "site id",
            "id",
            "station_id",
            "station id",
            "Site ID",
        ],
        default=str(index),
    )

    trading_name = pick(
        row,
        [
            "forecourts.trading_name",
            "trading_name",
            "trading name",
            "forecourts.siteName",
            "site_name",
            "sitename",
            "site name",
            "station_name",
            "name",
        ],
        "",
    )

    brand = pick(
        row,
        [
            "forecourts.brand_name",
            "brand_name",
            "brand name",
            "forecourts.brand",
            "brand",
            "operator",
            "company",
        ],
        "",
    )

    line1 = pick(row, ["forecourts.location.address_line_1", "address_line_1", "address line 1", "address1", "line1"], "")
    line2 = pick(row, ["forecourts.location.address_line_2", "address_line_2", "address line 2", "address2", "line2"], "")
    city = pick(row, ["forecourts.location.city", "city", "town"], "")
    county = pick(row, ["forecourts.location.county", "county"], "")
    country = pick(row, ["forecourts.location.country", "country"], "")
    postcode = pick(row, ["forecourts.location.postcode", "postcode", "post_code", "post code"], "")

    e5 = to_price(pick(row, ["forecourts.fuel_price.E5", "fuel_price.E5", "price.E5", "prices.E5", "e5", "E5", "super unleaded"]))
    e10 = to_price(pick(row, ["forecourts.fuel_price.E10", "fuel_price.E10", "price.E10", "prices.E10", "e10", "E10", "petrol"]))
    b7 = to_price(pick(row, ["forecourts.fuel_price.B7S", "fuel_price.B7S", "price.B7S", "prices.B7S", "forecourts.fuel_price.B7", "b7s", "B7S", "b7", "B7", "diesel"]))
    sdv = to_price(pick(row, ["forecourts.fuel_price.B7P", "fuel_price.B7P", "price.B7P", "prices.B7P", "b7p", "B7P", "sdv", "SDV", "premium diesel", "super diesel"]))

    e5_updated_at = pick(row, ["forecourts.price_submission_timestamp.E5", "price_submission_timestamp.E5", "prices.E5.lastUpdated", "E5.lastUpdated"], "")
    e10_updated_at = pick(row, ["forecourts.price_submission_timestamp.E10", "price_submission_timestamp.E10", "prices.E10.lastUpdated", "E10.lastUpdated"], "")
    b7_updated_at = pick(row, ["forecourts.price_submission_timestamp.B7S", "price_submission_timestamp.B7S", "forecourts.price_submission_timestamp.B7", "prices.B7.lastUpdated", "B7.lastUpdated", "diesel.lastUpdated"], "")
    sdv_updated_at = pick(row, ["forecourts.price_submission_timestamp.B7P", "price_submission_timestamp.B7P", "prices.B7P.lastUpdated", "B7P.lastUpdated"], "")

    lat = to_float(pick(row, ["forecourts.location.latitude", "location.latitude", "latitude", "lat"]))
    lng = to_float(pick(row, ["forecourts.location.longitude", "location.longitude", "longitude", "lng", "lon"]))

    station = {
        "id": str(station_id),
        "brand": str(brand or "").strip(),
        "name": str(trading_name or brand or "").strip(),
        "address": compact_address(line1, line2, city, county, country),
        "postcode": str(postcode or "").strip(),
        "lat": lat,
        "lng": lng,
        "e5": e5,
        "e10": e10,
        "b7": b7,
        "sdv": sdv,
        "e5_updated_at": e5_updated_at,
        "e10_updated_at": e10_updated_at,
        "b7_updated_at": b7_updated_at,
        "sdv_updated_at": sdv_updated_at,
        "opening_hours": opening_hours_from_row(row),
        "opening": format_opening_today(opening_hours_from_row(row)),
        "is_motorway": pick_bool(row, ["forecourts.is_motorway_service_station", "is_motorway_service_station", "motorway"]),
        "is_supermarket": pick_bool(row, ["forecourts.is_supermarket_service_station", "is_supermarket_service_station", "supermarket"]),
        "updated_at": pick(row, ["forecourt_update_timestamp", "updated_at", "last_updated", "last updated"], ""),
    }

    # Keep the station if it has enough information to be useful. This avoids
    # saving rows that would show as blank cards in future trend/tools pages.
    has_identity = station["name"] or station["brand"] or station["postcode"]
    has_location = station["lat"] is not None and station["lng"] is not None
    has_price = any(station[fuel] is not None for fuel in ["e5", "e10", "b7", "sdv"])

    if has_identity and has_location and has_price:
        usable_station_count += 1

    stations.append(station)

if usable_station_count == 0:
    write_status(
        "failed",
        "CSV parsed but no usable stations were found. Check CSV column names before overwriting latest.json.",
        row_count=len(rows),
        station_count=len(stations),
        usable_station_count=usable_station_count,
        columns=columns,
    )
    raise SystemExit("No usable stations found. latest.json was not overwritten.")

output = {
    "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source": "data/fuel_data.csv",
    "row_count": len(rows),
    "station_count": len(stations),
    "usable_station_count": usable_station_count,
    "stations": stations,
}

write_json(LATEST_FILE, output, compact=True)

write_status(
    "success",
    "latest.json generated successfully from data/fuel_data.csv.",
    row_count=len(rows),
    station_count=len(stations),
    usable_station_count=usable_station_count,
    columns=columns,
)

print(f"Generated {LATEST_FILE} with {len(stations)} stations ({usable_station_count} usable).")

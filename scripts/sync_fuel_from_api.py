import csv
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

CLIENT_ID = os.environ.get("FUEL_FINDER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_FINDER_CLIENT_SECRET")

TOKEN_URL = "https://www.fuel-finder.service.gov.uk/api/v1/oauth/generate_access_token"
PRICES_BASE_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices"
INFO_BASE_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs"

DATA_DIR = Path("data")
CSV_FILE = DATA_DIR / "fuel_data.csv"
LATEST_JSON = DATA_DIR / "latest.json"
STATUS_FILE = DATA_DIR / "api-sync-status.json"

MAX_BATCHES = 200
REQUEST_DELAY_SECONDS = 0.5

CSV_FIELDS = [
    "forecourt_update_timestamp",
    "forecourts.node_id",
    "forecourts.trading_name",
    "forecourts.brand_name",
    "forecourts.is_motorway_service_station",
    "forecourts.is_supermarket_service_station",
    "forecourts.public_phone_number",
    "forecourts.temporary_closure",
    "forecourts.permanent_closure",
    "forecourts.permanent_closure_date",
    "forecourts.location.postcode",
    "forecourts.location.address_line_1",
    "forecourts.location.address_line_2",
    "forecourts.location.city",
    "forecourts.location.county",
    "forecourts.location.country",
    "forecourts.location.latitude",
    "forecourts.location.longitude",
    "forecourts.fuel_price.E5",
    "forecourts.price_submission_timestamp.E5",
    "forecourts.price_change_effective_timestamp.E5",
    "forecourts.fuel_price.E10",
    "forecourts.price_submission_timestamp.E10",
    "forecourts.price_change_effective_timestamp.E10",
    "forecourts.fuel_price.B7S",
    "forecourts.price_submission_timestamp.B7S",
    "forecourts.price_change_effective_timestamp.B7S",
    "forecourts.fuel_price.B7P",
    "forecourts.price_submission_timestamp.B7P",
    "forecourts.price_change_effective_timestamp.B7P",
    "forecourts.fuel_price.B10",
    "forecourts.price_submission_timestamp.B10",
    "forecourts.price_change_effective_timestamp.B10",
    "forecourts.fuel_price.HVO",
    "forecourts.price_submission_timestamp.HVO",
    "forecourts.price_change_effective_timestamp.HVO",
    "forecourts.opening_times.usual_days.monday.open_time",
    "forecourts.opening_times.usual_days.monday.close_time",
    "forecourts.opening_times.usual_days.monday.is_24_hours",
    "forecourts.opening_times.usual_days.tuesday.open_time",
    "forecourts.opening_times.usual_days.tuesday.close_time",
    "forecourts.opening_times.usual_days.tuesday.is_24_hours",
    "forecourts.opening_times.usual_days.wednesday.open_time",
    "forecourts.opening_times.usual_days.wednesday.close_time",
    "forecourts.opening_times.usual_days.wednesday.is_24_hours",
    "forecourts.opening_times.usual_days.thursday.open_time",
    "forecourts.opening_times.usual_days.thursday.close_time",
    "forecourts.opening_times.usual_days.thursday.is_24_hours",
    "forecourts.opening_times.usual_days.friday.open_time",
    "forecourts.opening_times.usual_days.friday.close_time",
    "forecourts.opening_times.usual_days.friday.is_24_hours",
    "forecourts.opening_times.usual_days.saturday.open_time",
    "forecourts.opening_times.usual_days.saturday.close_time",
    "forecourts.opening_times.usual_days.saturday.is_24_hours",
    "forecourts.opening_times.usual_days.sunday.open_time",
    "forecourts.opening_times.usual_days.sunday.close_time",
    "forecourts.opening_times.usual_days.sunday.is_24_hours",
    "forecourts.opening_times.bank_holiday.standard.open_time",
    "forecourts.opening_times.bank_holiday.standard.close_time",
    "forecourts.opening_times.bank_holiday.standard.is_24_hours",
    "forecourts.amenities.fuel_and_energy_services.adblue_pumps",
    "forecourts.amenities.fuel_and_energy_services.adblue_packaged",
    "forecourts.amenities.fuel_and_energy_services.lpg_pumps",
    "forecourts.amenities.vehicle_services.car_wash",
    "forecourts.amenities.air_pump_or_screenwash",
    "forecourts.amenities.water_filling",
    "forecourts.amenities.twenty_four_hour_fuel",
    "forecourts.amenities.customer_toilets",
]

FUEL_MAP = {
    "E5": "E5",
    "E10": "E10",
    "B7_STANDARD": "B7S",
    "B7S": "B7S",
    "B7_PREMIUM": "B7P",
    "B7P": "B7P",
    "B10": "B10",
    "HVO": "HVO",
}

AMENITY_MAP = {
    "forecourts.amenities.fuel_and_energy_services.adblue_pumps": "adblue_pumps",
    "forecourts.amenities.fuel_and_energy_services.adblue_packaged": "adblue_packaged",
    "forecourts.amenities.fuel_and_energy_services.lpg_pumps": "lpg_pumps",
    "forecourts.amenities.vehicle_services.car_wash": "car_wash",
    "forecourts.amenities.air_pump_or_screenwash": "air_pump_or_screenwash",
    "forecourts.amenities.water_filling": "water_filling",
    "forecourts.amenities.twenty_four_hour_fuel": "twenty_four_hour_fuel",
    "forecourts.amenities.customer_toilets": "customer_toilets",
}

def fail(message):
    raise SystemExit(message)

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

def js_date_now():
    return datetime.now(timezone.utc).strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)")

def to_csv_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value

def request_json(url, method="GET", token=None, payload=None, label="API", allow_404=False):
    headers = {
        "Accept": "application/json",
        "User-Agent": "Driverz.uk NAS fuel sync contact: mtamtc76@gmail.com",
    }

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        if allow_404 and exc.code == 404:
            print(f"{label}: batch not available. Stopping.")
            return None

        print(f"{label} failed with HTTP {exc.code}")
        print(exc.headers)
        print(body[:1000])
        raise

def get_token():
    if not CLIENT_ID:
        fail("Missing FUEL_FINDER_CLIENT_ID")

    if not CLIENT_SECRET:
        fail("Missing FUEL_FINDER_CLIENT_SECRET")

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    token_response = request_json(
        TOKEN_URL,
        method="POST",
        payload=payload,
        label="Token request",
    )

    token = None

    if isinstance(token_response.get("data"), dict):
        token = token_response["data"].get("access_token")

    token = token or token_response.get("access_token")

    if not token:
        print(json.dumps(token_response, indent=2)[:1500])
        fail("No access token found.")

    return token

def fetch_all_batches(base_url, token, label):
    results = []

    for batch in range(1, MAX_BATCHES + 1):
        url = f"{base_url}?batch-number={batch}"
        print(f"Fetching {label} batch {batch}...")

        batch_data = request_json(
            url,
            token=token,
            label=f"{label} batch {batch}",
            allow_404=True,
        )

        if not batch_data:
            print(f"No data returned for {label} batch {batch}. Stopping.")
            break

        if not isinstance(batch_data, list):
            print(json.dumps(batch_data, indent=2)[:1500])
            fail(f"Unexpected response format for {label} batch {batch}")

        results.extend(batch_data)
        print(f"{label} batch {batch}: {len(batch_data)} records")

        time.sleep(REQUEST_DELAY_SECONDS)

    return results

def get_day(opening_times, day):
    usual_days = (opening_times or {}).get("usual_days") or {}
    return usual_days.get(day) or {}

def get_bank_holiday(opening_times):
    bank = (opening_times or {}).get("bank_holiday") or {}
    return bank.get("standard") or {}

def get_open(day_obj):
    return day_obj.get("open_time") or day_obj.get("open") or ""

def get_close(day_obj):
    return day_obj.get("close_time") or day_obj.get("close") or ""

def get_24(day_obj):
    return to_csv_value(day_obj.get("is_24_hours"))

def build_price_lookup(price_records):
    lookup = {}

    for record in price_records:
        node_id = record.get("node_id")
        if not node_id:
            continue

        fuels = {}

        for item in record.get("fuel_prices", []) or []:
            raw_type = item.get("fuel_type")
            mapped_type = FUEL_MAP.get(raw_type)

            if not mapped_type:
                continue

            fuels[mapped_type] = {
                "price": item.get("price"),
                "price_last_updated": item.get("price_last_updated"),
                "price_change_effective_timestamp": item.get("price_change_effective_timestamp"),
            }

        lookup[node_id] = {
            "public_phone_number": record.get("public_phone_number"),
            "trading_name": record.get("trading_name"),
            "fuels": fuels,
        }

    return lookup

def build_csv_rows(info_records, price_lookup):
    rows = []
    now_text = js_date_now()

    for info in info_records:
        node_id = info.get("node_id")
        location = info.get("location") or {}
        opening_times = info.get("opening_times") or {}
        amenities = set(info.get("amenities") or [])
        price_info = price_lookup.get(node_id, {})
        fuels = price_info.get("fuels", {})

        row = {field: "" for field in CSV_FIELDS}

        row["forecourt_update_timestamp"] = now_text
        row["forecourts.node_id"] = node_id or ""
        row["forecourts.trading_name"] = info.get("trading_name") or price_info.get("trading_name") or ""
        row["forecourts.brand_name"] = info.get("brand_name") or ""
        row["forecourts.is_motorway_service_station"] = to_csv_value(info.get("is_motorway_service_station"))
        row["forecourts.is_supermarket_service_station"] = to_csv_value(info.get("is_supermarket_service_station"))
        row["forecourts.public_phone_number"] = info.get("public_phone_number") or price_info.get("public_phone_number") or ""
        row["forecourts.temporary_closure"] = to_csv_value(info.get("temporary_closure"))
        row["forecourts.permanent_closure"] = to_csv_value(info.get("permanent_closure"))
        row["forecourts.permanent_closure_date"] = info.get("permanent_closure_date") or ""

        row["forecourts.location.postcode"] = location.get("postcode") or ""
        row["forecourts.location.address_line_1"] = location.get("address_line_1") or ""
        row["forecourts.location.address_line_2"] = location.get("address_line_2") or ""
        row["forecourts.location.city"] = location.get("city") or ""
        row["forecourts.location.county"] = location.get("county") or ""
        row["forecourts.location.country"] = location.get("country") or ""
        row["forecourts.location.latitude"] = location.get("latitude") or ""
        row["forecourts.location.longitude"] = location.get("longitude") or ""

        for fuel in ["E5", "E10", "B7S", "B7P", "B10", "HVO"]:
            fuel_data = fuels.get(fuel) or {}
            row[f"forecourts.fuel_price.{fuel}"] = fuel_data.get("price") or ""
            row[f"forecourts.price_submission_timestamp.{fuel}"] = fuel_data.get("price_last_updated") or ""
            row[f"forecourts.price_change_effective_timestamp.{fuel}"] = fuel_data.get("price_change_effective_timestamp") or ""

        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            day_obj = get_day(opening_times, day)
            row[f"forecourts.opening_times.usual_days.{day}.open_time"] = get_open(day_obj)
            row[f"forecourts.opening_times.usual_days.{day}.close_time"] = get_close(day_obj)
            row[f"forecourts.opening_times.usual_days.{day}.is_24_hours"] = get_24(day_obj)

        bank = get_bank_holiday(opening_times)
        row["forecourts.opening_times.bank_holiday.standard.open_time"] = get_open(bank)
        row["forecourts.opening_times.bank_holiday.standard.close_time"] = get_close(bank)
        row["forecourts.opening_times.bank_holiday.standard.is_24_hours"] = get_24(bank)

        for csv_field, api_name in AMENITY_MAP.items():
            row[csv_field] = "true" if api_name in amenities else "false"

        rows.append(row)

    return rows

def build_latest_json(rows):
    stations = []

    for row in rows:
        stations.append({
            "id": row.get("forecourts.node_id", ""),
            "brand": row.get("forecourts.brand_name", ""),
            "name": row.get("forecourts.trading_name", ""),
            "address": row.get("forecourts.location.address_line_1", ""),
            "postcode": row.get("forecourts.location.postcode", ""),
            "lat": float(row["forecourts.location.latitude"]) if row.get("forecourts.location.latitude") not in ("", None) else None,
            "lng": float(row["forecourts.location.longitude"]) if row.get("forecourts.location.longitude") not in ("", None) else None,
            "e5": float(row["forecourts.fuel_price.E5"]) if row.get("forecourts.fuel_price.E5") not in ("", None) else None,
            "e10": float(row["forecourts.fuel_price.E10"]) if row.get("forecourts.fuel_price.E10") not in ("", None) else None,
            "b7": float(row["forecourts.fuel_price.B7S"]) if row.get("forecourts.fuel_price.B7S") not in ("", None) else None,
            "sdv": float(row["forecourts.fuel_price.B7P"]) if row.get("forecourts.fuel_price.B7P") not in ("", None) else None,
        })

    return {
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "generated_at": utc_now_iso(),
        "source": "GOV Fuel Finder API via Synology NAS",
        "station_count": len(stations),
        "stations": stations,
    }

def write_csv(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    started_at = utc_now_iso()

    print("Getting access token...")
    token = get_token()
    print("Access token received.")

    price_records = fetch_all_batches(PRICES_BASE_URL, token, "fuel prices")
    info_records = fetch_all_batches(INFO_BASE_URL, token, "forecourt info")

    print(f"Total price records: {len(price_records)}")
    print(f"Total info records: {len(info_records)}")

    if not price_records:
        fail("No fuel price records downloaded.")

    if not info_records:
        fail("No forecourt info records downloaded.")

    price_lookup = build_price_lookup(price_records)
    rows = build_csv_rows(info_records, price_lookup)

    if not rows:
        fail("No rows generated.")

    write_csv(rows)
    latest_payload = build_latest_json(rows)
    write_json(LATEST_JSON, latest_payload)

    status = {
        "status": "success",
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "price_records": len(price_records),
        "info_records": len(info_records),
        "csv_rows": len(rows),
        "csv_file": str(CSV_FILE),
        "latest_json": str(LATEST_JSON),
    }

    write_json(STATUS_FILE, status)

    print("Fuel API sync completed.")
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
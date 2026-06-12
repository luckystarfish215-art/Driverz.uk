#!/usr/bin/env python3
import csv
import json
import os
import re
from datetime import datetime

CONFIG_PATH = "config/device-config.json"
CSV_PATH = "data/fuel_data.csv"
OUTPUT_PATH = "device-demo.json"

def clean(value):
    return "" if value is None else str(value).strip()

def parse_price(value):
    text = clean(value)
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    price = float(match.group(1))
    return price if 50 <= price <= 300 else None

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(f"ERROR: {CONFIG_PATH} not found")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def row_text(row):
    return " ".join(clean(v).lower() for v in row.values() if clean(v))

def score_row(row, query):
    text = row_text(row)
    query = query.lower().strip()
    tokens = [t for t in query.split() if t]

    score = 0

    if query and query in text:
        score += 100

    for token in tokens:
        if token in text:
            score += 10

    return score

def find_station(rows, station_query, station_node_id):
    station_node_id = clean(station_node_id)

    if station_node_id:
        for row in rows:
            if clean(row.get("forecourts.node_id")) == station_node_id:
                return row

        raise SystemExit(f"ERROR: stationNodeId not found: {station_node_id}")

    best = None
    best_score = 0

    for row in rows:
        score = score_row(row, station_query)
        if score > best_score:
            best = row
            best_score = score

    if best is None:
        raise SystemExit(f"ERROR: station not found for query: {station_query}")

    return best

def find_price_and_timestamp(row, fuel):
    fuel = fuel.lower()

    if fuel == "diesel":
        price_keys = [
            "forecourts.fuel_price.B7S",
            "forecourts.fuel_price.B7",
            "forecourts.fuel_price.B7P"
        ]
        timestamp_keys = [
            "forecourts.price_change_effective_timestamp.B7S",
            "forecourts.price_submission_timestamp.B7S",
            "forecourts.price_change_effective_timestamp.B7",
            "forecourts.price_submission_timestamp.B7",
            "forecourts.price_change_effective_timestamp.B7P",
            "forecourts.price_submission_timestamp.B7P"
        ]
        fuel_label = "Diesel"

    elif fuel in ["petrol", "e10"]:
        price_keys = ["forecourts.fuel_price.E10"]
        timestamp_keys = [
            "forecourts.price_change_effective_timestamp.E10",
            "forecourts.price_submission_timestamp.E10"
        ]
        fuel_label = "Petrol E10"

    elif fuel == "e5":
        price_keys = ["forecourts.fuel_price.E5"]
        timestamp_keys = [
            "forecourts.price_change_effective_timestamp.E5",
            "forecourts.price_submission_timestamp.E5"
        ]
        fuel_label = "Petrol E5"

    else:
        raise SystemExit(f"ERROR: unsupported fuel type: {fuel}")

    price = None
    for key in price_keys:
        price = parse_price(row.get(key))
        if price is not None:
            break

    timestamp = ""
    for key in timestamp_keys:
        value = clean(row.get(key))
        if value:
            timestamp = value
            break

    return price, timestamp, fuel_label

def format_timestamp(ts):
    if not ts:
        return "Updated unknown"

    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return "Updated " + dt.astimezone().strftime("%H:%M")
    except Exception:
        return "Updated " + ts[:16]

def make_station_name(row, fallback, display_name=""):
    display_name = clean(display_name)
    if display_name:
        return display_name.upper()[:24]

    brand = clean(row.get("forecourts.brand_name"))
    trading = clean(row.get("forecourts.trading_name"))
    city = clean(row.get("forecourts.location.city"))
    postcode = clean(row.get("forecourts.location.postcode"))

    trading = trading.replace(" - PETROL FILLING STATION", "")
    trading = trading.replace("PETROL FILLING STATION", "")
    trading = trading.replace("PFS", "")
    trading = " ".join(trading.split())

    if brand and trading:
        name = f"{brand} {trading}"
    elif brand and city:
        name = f"{brand} {city}"
    elif trading:
        name = trading
    elif brand and postcode:
        name = f"{brand} {postcode}"
    else:
        name = fallback

    name = name.upper()

    if len(name) > 24:
        name = name[:24]

    return name

def main():
    config = load_config()

    station_query = clean(config.get("stationQuery", ""))
    station_node_id = clean(config.get("stationNodeId", ""))
    fuel = clean(config.get("fuel", "diesel")).lower()
    weather_text = clean(config.get("weatherText", "19C Cloud"))
    air_text = clean(config.get("airText", "Air Good"))

    if not os.path.exists(CSV_PATH):
        raise SystemExit("ERROR: data/fuel_data.csv not found")

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("ERROR: fuel_data.csv is empty")

    row = find_station(rows, station_query, station_node_id)

    price, price_timestamp, fuel_label = find_price_and_timestamp(row, fuel)

    if price is None:
        print("Matched station but price not found:")
        for k, v in row.items():
            if v:
                print(k, "=", v)
        raise SystemExit("ERROR: fuel price not found")

    output = {
        "stationName": make_station_name(row, station_query, config.get("displayName", "")),
        "fuelType": fuel_label,
        "fuelPrice": f"{price:.1f}p",
        "priceChange": "Latest price",
        "updatedTime": format_timestamp(price_timestamp),
        "weatherText": weather_text,
        "airText": air_text
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print("Generated device-demo.json")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()

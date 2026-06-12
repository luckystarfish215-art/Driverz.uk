#!/usr/bin/env python3
import csv
import json
import os
import re
from datetime import datetime, timezone

QUERY = "TESCO READING"
FUEL = "diesel"
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

def row_text(row):
    return " ".join(clean(v).lower() for v in row.values() if clean(v))

def score_row(row, query):
    text = row_text(row)
    query = query.lower()
    tokens = query.split()

    score = 0
    if query in text:
        score += 100

    for token in tokens:
        if token in text:
            score += 10

    return score

def get_value(row, key):
    return clean(row.get(key, ""))

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

    elif fuel in ["petrol", "e10"]:
        price_keys = [
            "forecourts.fuel_price.E10"
        ]
        timestamp_keys = [
            "forecourts.price_change_effective_timestamp.E10",
            "forecourts.price_submission_timestamp.E10"
        ]

    elif fuel == "e5":
        price_keys = [
            "forecourts.fuel_price.E5"
        ]
        timestamp_keys = [
            "forecourts.price_change_effective_timestamp.E5",
            "forecourts.price_submission_timestamp.E5"
        ]

    else:
        price_keys = []
        timestamp_keys = []

    price = None

    for key in price_keys:
        price = parse_price(row.get(key))
        if price is not None:
            break

    timestamp = ""

    for key in timestamp_keys:
        value = get_value(row, key)
        if value:
            timestamp = value
            break

    return price, timestamp

def format_timestamp(ts):
    if not ts:
        return "Updated unknown"

    try:
        # Example: 2026-06-11T17:40:21.000Z
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        return "Updated " + local_dt.strftime("%H:%M")
    except Exception:
        return "Updated " + ts[:16]

def make_station_name(row):
    brand = get_value(row, "forecourts.brand_name")
    trading = get_value(row, "forecourts.trading_name")
    city = get_value(row, "forecourts.location.city")
    postcode = get_value(row, "forecourts.location.postcode")

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
        name = QUERY

    name = name.upper()

    # ESP32 header readability
    if len(name) > 24:
        name = name[:24]

    return name

def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit("ERROR: data/fuel_data.csv not found")

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("ERROR: fuel_data.csv is empty")

    best = None
    best_score = 0

    for row in rows:
        score = score_row(row, QUERY)
        if score > best_score:
            best = row
            best_score = score

    if best is None:
        raise SystemExit("ERROR: station not found")

    price, price_timestamp = find_price_and_timestamp(best, FUEL)

    if price is None:
        print("Matched row but price not found. Columns:")
        for k, v in best.items():
            if v:
                print(k, "=", v)
        raise SystemExit("ERROR: fuel price not found")

    fuel_label = "Diesel" if FUEL == "diesel" else "Petrol E10"

    data = {
        "stationName": make_station_name(best),
        "fuelType": fuel_label,
        "fuelPrice": f"{price:.1f}p",
        "priceChange": "Latest price",
      
        "weatherText": "
        "airText": "Air G
    }

    with open(OUTPU

        f.wri

    print("Generated
    print(json.dumpsdent=2))

if __name__ == "__main__":
    main()

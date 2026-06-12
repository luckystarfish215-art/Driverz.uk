#!/usr/bin/env python3
import csv
import json
import os
import re
from datetime import datetime

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

def find_price(row, fuel):
    preferred = ["b7", "diesel"] if fuel == "diesel" else ["e10", "petrol"]

    for key, value in row.items():
        key_l = key.lower()
        if any(p in key_l for p in preferred):
            price = parse_price(value)
            if price is not None:
                return price

    return None

def find_station_name(row):
    for key in row.keys():
        key_l = key.lower()
        if key_l in ["stationname", "station_name", "sitename", "site_name", "name"]:
            value = clean(row[key])
            if value:
                return value.upper()[:24]

    for key in row.keys():
        if "brand" in key.lower() or "retailer" in key.lower():
            value = clean(row[key])
            if value:
                return value.upper()[:24]

    return QUERY.upper()[:24]

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

    price = find_price(best, FUEL)

    if price is None:
        print("Matched row but price not found. Columns:")
        for k, v in best.items():
            print(k, "=", v)
        raise SystemExit("ERROR: diesel price not found")

    now_text = datetime.now().strftime("%H:%M")

    data = {
        "stationName": find_station_name(best),
        "fuelType": "Diesel",
        "fuelPrice": f"{price:.1f}p",
        "priceChange": "Latest price",
        "updatedTime": f"Updated {now_text}",
        "weatherText": "19C Cloud",
        "airText": "Air Good"
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print("Generated device-demo.json")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()

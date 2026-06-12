#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
from datetime import datetime

def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())

def parse_price(value):
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        price = float(match.group(1))
        if 50 <= price <= 300:
            return price
    except ValueError:
        return None
    return None

def read_csv_records(path):
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def flatten_json_records(obj):
    records = []

    if isinstance(obj, list):
        for item in obj:
            records.extend(flatten_json_records(item))

    elif isinstance(obj, dict):
        price_like = False
        for key, value in obj.items():
            k = norm(key)
            if k in ("b7", "e10", "e5") or "diesel" in k or "petrol" in k:
                if parse_price(value) is not None:
                    price_like = True

        if price_like:
            records.append(obj)

        for value in obj.values():
            if isinstance(value, (dict, list)):
                records.extend(flatten_json_records(value))

    return records

def read_json_records(path):
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return flatten_json_records(data)

def combined_record_text(row):
    useful_parts = []
    for key, value in row.items():
        text = clean_text(value)
        if text and len(text) < 120:
            useful_parts.append(text)
    return " ".join(useful_parts).lower()

def score_record(row, query):
    query_lower = query.lower().strip()
    tokens = [t for t in re.split(r"\s+", query_lower) if t]

    text = combined_record_text(row)

    if not tokens:
        return 0

    score = 0

    if query_lower in text:
        score += 100

    for token in tokens:
        if token in text:
            score += 10

    # Prefer records that contain a usable price
    for value in row.values():
        if parse_price(value) is not None:
            score += 1
            break

    return score

def find_best_record(records, query):
    scored = []
    for row in records:
        s = score_record(row, query)
        if s > 0:
            scored.append((s, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return None

    return scored[0][1]

def find_fuel_price(row, fuel):
    fuel = fuel.lower().strip()

    if fuel in ("diesel", "b7"):
        preferred = ["b7", "diesel"]
    elif fuel in ("petrol", "e10"):
        preferred = ["e10", "petrol", "unleaded"]
    elif fuel == "e5":
        preferred = ["e5", "super", "premium"]
    else:
        preferred = [fuel]

    # First pass: column names that clearly match fuel type
    for key, value in row.items():
        k = norm(key)
        for p in preferred:
            if p in k:
                price = parse_price(value)
                if price is not None:
                    return price

    # Second pass: exact GOV style short columns
    exact_map = {
        "diesel": ["b7"],
        "b7": ["b7"],
        "petrol": ["e10"],
        "e10": ["e10"],
        "e5": ["e5"]
    }

    for col in exact_map.get(fuel, []):
        for key, value in row.items():
            if norm(key) == col:
                price = parse_price(value)
                if price is not None:
                    return price

    return None

def get_first(row, candidates):
    candidate_norms = [norm(c) for c in candidates]

    for key, value in row.items():
        if norm(key) in candidate_norms:
            text = clean_text(value)
            if text:
                return text

    for key, value in row.items():
        k = norm(key)
        for candidate in candidate_norms:
            if candidate in k:
                text = clean_text(value)
                if text:
                    return text

    return ""

def make_station_display_name(row, fallback_query):
    station = get_first(row, [
        "stationName", "station_name", "siteName", "site_name",
        "name", "tradingName", "trading_name"
    ])

    brand = get_first(row, [
        "brand", "retailer", "company", "operator"
    ])

    town = get_first(row, [
        "town", "city", "locality"
    ])

    postcode = get_first(row, [
        "postcode", "post_code"
    ])

    address = get_first(row, [
        "address", "street", "siteAddress", "site_address"
    ])

    if station:
        display = station
    elif brand and town:
        display = f"{brand} {town}"
    elif brand and postcode:
        display = f"{brand} {postcode}"
    elif brand and address:
        display = f"{brand} {address}"
    else:
        display = fallback_query

    display = display.upper()

    # Keep ESP32 header readable
    if len(display) > 24:
        display = display[:24]

    return display

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="TESCO READING", help="Station search text")
    parser.add_argument("--fuel", default="diesel", help="diesel, e10, petrol, e5")
    parser.add_argument("--csv", default="data/fuel_data.csv")
    parser.add_argument("--json", default="data/latest.json")
    parser.add_argument("--output", default="device-demo.json")
    parser.add_argument("--weather", default="19C Cloud")
    parser.add_argument("--air", default="Air Good")
    args = parser.parse_args()

    records = read_csv_records(args.csv)

    source = args.csv

    if not records:
        records = read_json_records(args.json)
        source = args.json

    if not records:
        raise SystemExit("ERROR: No fuel records found in data/fuel_data.csv or data/latest.json")

    row = find_best_record(records, args.query)

    if row is None:
        raise SystemExit(f"ERROR: No station matched query: {args.query}")

    price = find_fuel_price(row, args.fuel)

    if price is None:
        print("Matched station, but could not find fuel price.")
        print("Available columns:")
        for key in row.keys():
            print(f" - {key}: {row.get(key)}")
        raise SystemExit("ERROR: Fuel price not found for selected fuel type")

    station_name = make_station_display_name(row, args.query)

    fuel_label_map = {
        "diesel": "Diesel",
        "b7": "Diesel",
        "petrol": "Petrol E10",
        "e10": "Petrol E10",
        "e5": "Petrol E5"
    }

    fuel_label = fuel_label_map.get(args.fuel.lower(), args.fuel.title())

    now_text = datetime.now().strftime("%H:%M")

    output = {
        "stationName": station_name,
        "fuelType": fuel_label,
        "fuelPrice": f"{price:.1f}p",
        "priceChange": "Latest price",
        "updatedTime": f"Updated {now_text}",
        "weatherText": args.weather,
        "airText": args.air
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print("Device JSON generated successfully.")
    print(f"Source: {source}")
    print(f"Query: {args.query}")
    print(f"Fuel: {fuel_label}")
    print(f"Price: {price:.1f}p")
    print(f"Output: {args.output}")

if __name__ == "__main__":
    main()

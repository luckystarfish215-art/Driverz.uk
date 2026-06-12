#!/usr/bin/env python3
import csv
import sys
import re

CSV_PATH = "data/fuel_data.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def row_text(row):
    return " ".join(clean(v).lower() for v in row.values() if clean(v))

def score_row(row, query):
    text = row_text(row)
    query = query.lower().strip()
    tokens = [t for t in re.split(r"\s+", query) if t]

    score = 0
    if query in text:
        score += 100

    for token in tokens:
        if token in text:
            score += 10

    return score

def price(row, key):
    v = clean(row.get(key))
    return v if v else "-"

def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/find_device_station.py "COSTCO READING"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    matches = []

    for row in rows:
        score = score_row(row, query)
        if score > 0:
            matches.append((score, row))

    matches.sort(key=lambda x: x[0], reverse=True)

    if not matches:
        print(f"No stations found for: {query}")
        sys.exit(1)

    print(f"Top matches for: {query}")
    print("=" * 80)

    for i, (score, row) in enumerate(matches[:15], 1):
        brand = clean(row.get("forecourts.brand_name"))
        trading = clean(row.get("forecourts.trading_name"))
        postcode = clean(row.get("forecourts.location.postcode"))
        city = clean(row.get("forecourts.location.city"))
        address1 = clean(row.get("forecourts.location.address_line_1"))
        address2 = clean(row.get("forecourts.location.address_line_2"))
        node_id = clean(row.get("forecourts.node_id"))

        print(f"\n[{i}] {brand} - {trading}")
        print(f"    Address: {address1}, {address2}")
        print(f"    City: {city}")
        print(f"    Postcode: {postcode}")
        print(f"    E10: {price(row, 'forecourts.fuel_price.E10')}p")
        print(f"    E5 : {price(row, 'forecourts.fuel_price.E5')}p")
        print(f"    B7S: {price(row, 'forecourts.fuel_price.B7S')}p")
        print(f"    B7P: {price(row, 'forecourts.fuel_price.B7P')}p")
        print(f"    node_id: {node_id}")

if __name__ == "__main__":
    main()

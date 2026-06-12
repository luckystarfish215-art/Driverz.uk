#!/usr/bin/env python3
import csv
import json
import os
import re

CSV_PATH = "data/fuel_data.csv"
OUTPUT_PATH = "device/stations.json"

def clean(v):
    return "" if v is None else str(v).strip()

def price(v):
    text = clean(v)
    if not text:
        return ""
    try:
        n = float(text)
        if 50 <= n <= 300:
            return f"{n:.1f}"
    except ValueError:
        pass
    return ""

def display_name(brand, trading, city):
    brand = clean(brand)
    trading = clean(trading)
    city = clean(city)

    trading = trading.replace(" - PETROL FILLING STATION", "")
    trading = trading.replace("PETROL FILLING STATION", "")
    trading = trading.replace("PFS", "")
    trading = " ".join(trading.split())

    if "COSTCO WHOLESALE READING" in trading.upper():
        return "COSTCO READING"

    if brand and trading:
        name = f"{brand} {trading}"
    elif brand and city:
        name = f"{brand} {city}"
    elif trading:
        name = trading
    elif brand:
        name = brand
    else:
        name = "FUEL STATION"

    name = name.upper()

    if len(name) > 28:
        name = name[:28]

    return name

def make_search_text(parts):
    text = " ".join(clean(p).lower() for p in parts if clean(p))
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit("ERROR: data/fuel_data.csv not found")

    os.makedirs("device", exist_ok=True)

    stations = []

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            node_id = clean(row.get("forecourts.node_id"))
            brand = clean(row.get("forecourts.brand_name"))
            trading = clean(row.get("forecourts.trading_name"))
            city = clean(row.get("forecourts.location.city"))
            postcode = clean(row.get("forecourts.location.postcode"))
            address1 = clean(row.get("forecourts.location.address_line_1"))
            address2 = clean(row.get("forecourts.location.address_line_2"))

            e10 = price(row.get("forecourts.fuel_price.E10"))
            e5 = price(row.get("forecourts.fuel_price.E5"))
            diesel = price(row.get("forecourts.fuel_price.B7S")) or price(row.get("forecourts.fuel_price.B7P"))

            if not node_id:
                continue

            if not (e10 or e5 or diesel):
                continue

            name = display_name(brand, trading, city)

            station = {
                "nodeId": node_id,
                "brand": brand,
                "name": trading,
                "displayName": name,
                "address": ", ".join(x for x in [address1, address2] if x),
                "city": city,
                "postcode": postcode,
                "e10": e10,
                "e5": e5,
                "diesel": diesel,
                "searchText": make_search_text([
                    brand,
                    trading,
                    name,
                    address1,
                    address2,
                    city,
                    postcode
                ])
            }

            stations.append(station)

    stations.sort(key=lambda s: (s["city"], s["brand"], s["name"]))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(stations, f, separators=(",", ":"))
        f.write("\n")

    print(f"Generated {OUTPUT_PATH}")
    print(f"Stations: {len(stations)}")
    print(f"Size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import calendar
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "history" / "daily"
MONTHLY_DIR = ROOT / "history" / "monthly"

FUEL_TYPES = ("e10", "e5", "b7", "sdv")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_stations(payload):
    """
    Support the common Driverz snapshot shapes:
      1. [...]
      2. {"stations": [...]}
      3. {"data": [...]}
    """
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("stations", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("Unsupported daily snapshot JSON structure")


def get_price(station, fuel_type):
    """
    Support:
      {"prices": {"e10": 135.9}}
    and:
      {"e10": 135.9}
    """
    prices = station.get("prices")

    if isinstance(prices, dict):
        value = prices.get(fuel_type)
    else:
        value = station.get(fuel_type)

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if value <= 0:
        return None

    return value


def discover_months():
    months = set()

    for path in DAILY_DIR.glob("????-??-??.json"):
        months.add(path.stem[:7])

    return sorted(months)


def generate_month(month):
    paths = sorted(DAILY_DIR.glob(f"{month}-??.json"))

    if not paths:
        print(f"No snapshots found for {month}")
        return False

    daily_averages = defaultdict(list)
    valid_station_prices = defaultdict(int)
    skipped_files = []

    for path in paths:
        try:
            payload = load_json(path)
            stations = extract_stations(payload)
        except Exception as exc:
            skipped_files.append({
                "file": path.name,
                "error": str(exc),
            })
            continue

        day_values = defaultdict(list)

        for station in stations:
            if not isinstance(station, dict):
                continue

            for fuel_type in FUEL_TYPES:
                price = get_price(station, fuel_type)

                if price is not None:
                    day_values[fuel_type].append(price)
                    valid_station_prices[fuel_type] += 1

        for fuel_type, values in day_values.items():
            if values:
                daily_averages[fuel_type].append(
                    {
                        "date": path.stem,
                        "average": sum(values) / len(values),
                    }
                )

    fuel_summary = {}

    for fuel_type in FUEL_TYPES:
        rows = daily_averages.get(fuel_type, [])

        if not rows:
            continue

        averages = [row["average"] for row in rows]

        start_average = rows[0]["average"]
        end_average = rows[-1]["average"]

        fuel_summary[fuel_type] = {
            "days_available": len(rows),
            "average": round(sum(averages) / len(averages), 3),
            "minimum_daily_average": round(min(averages), 3),
            "maximum_daily_average": round(max(averages), 3),
            "start_average": round(start_average, 3),
            "end_average": round(end_average, 3),
            "change": round(end_average - start_average, 3),
            "valid_station_prices": valid_station_prices[fuel_type],
        }

    output = {
        "schema_version": 1,
        "month": month,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_files_found": len(paths),
        "snapshot_files_processed": len(paths) - len(skipped_files),
        "first_snapshot": paths[0].stem,
        "last_snapshot": paths[-1].stem,
        "fuel_types": fuel_summary,
        "skipped_files": skipped_files,
    }

    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MONTHLY_DIR / f"{month}.json"

    year, month_number = map(int, month.split("-"))
    expected_days = calendar.monthrange(year, month_number)[1]
    new_processed = output["snapshot_files_processed"]

    if output_path.exists():
        try:
            existing = load_json(output_path)
        except Exception as exc:
            print(
                f"Warning: existing monthly summary cannot be read "
                f"({output_path.relative_to(ROOT)}): {exc}"
            )
            existing = None

        if isinstance(existing, dict):
            existing_processed = existing.get(
                "snapshot_files_processed",
                0,
            )

            existing_is_complete = (
                existing.get("month") == month
                and not existing.get("skipped_files")
                and existing_processed == expected_days
            )

            new_is_incomplete = (
                skipped_files
                or new_processed != expected_days
            )

            if existing_is_complete and new_is_incomplete:
                print(
                    f"Protected complete monthly summary "
                    f"{output_path.relative_to(ROOT)}: "
                    f"refusing to overwrite with "
                    f"{new_processed}/{expected_days} days"
                )
                return False

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"Generated {output_path.relative_to(ROOT)} "
        f"from {len(paths) - len(skipped_files)}/{len(paths)} snapshots"
    )

    return True


def main():
    if not DAILY_DIR.exists():
        raise SystemExit(f"Daily history directory not found: {DAILY_DIR}")

    if len(sys.argv) == 1:
        months = discover_months()
    elif len(sys.argv) == 2:
        month = sys.argv[1]

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise SystemExit("Usage: generate_monthly_history.py [YYYY-MM]")

        months = [month]
    else:
        raise SystemExit("Usage: generate_monthly_history.py [YYYY-MM]")

    if not months:
        raise SystemExit("No daily snapshots found")

    generated = 0

    for month in months:
        if generate_month(month):
            generated += 1

    print(f"Monthly history generation complete: {generated} month(s)")


if __name__ == "__main__":
    main()

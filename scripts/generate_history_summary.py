#!/usr/bin/env python3
"""Generate a compact per-station fuel history summary for Driverz.

Reads history/daily/*.json snapshots and writes data/history-summary.json.
The API uses this small summary to add "since yesterday" and "7-day trend"
metadata to the selected main fuel card without loading daily snapshots at runtime.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, date, timedelta
from glob import glob
from pathlib import Path
from typing import Any

HISTORY_DIR = Path("history/daily")
OUTPUT_FILE = Path("data/history-summary.json")
MAX_SNAPSHOTS = 30
FUEL_MAP = {
    "petrol": "e10",
    "diesel": "b7",
}
MIN_PRICE = 80.0
MAX_PRICE = 300.0


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def parse_snapshot_date(value: str, fallback: str) -> date | None:
    raw = (value or fallback or "").strip()
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def normalise_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if MIN_PRICE <= price <= MAX_PRICE:
        return round(price, 1)
    return None


def price_map(snapshot: dict[str, Any], fuel_key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for station in snapshot.get("stations", []) or []:
        sid = str(station.get("id") or "").strip()
        if not sid:
            continue
        price = normalise_price(station.get(fuel_key))
        if price is not None:
            out[sid] = price
    return out


def change_payload(latest_price: float | None, reference_price: float | None, reference_date: str | None) -> dict[str, Any] | None:
    if latest_price is None or reference_price is None or reference_date is None:
        return None
    return {
        "reference_price": reference_price,
        "reference_date": reference_date,
        "change": round(latest_price - reference_price, 1),
    }


def main() -> None:
    files = [Path(p) for p in sorted(glob(str(HISTORY_DIR / "*.json")))]
    files = files[-MAX_SNAPSHOTS:]

    loaded: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for path in files:
        try:
            payload = read_json(path)
            stations = payload.get("stations", [])
            if not isinstance(stations, list) or not stations:
                raise ValueError("missing_or_empty_stations")
            snap_date = parse_snapshot_date(str(payload.get("snapshot_date") or ""), path.stem)
            if snap_date is None:
                raise ValueError("invalid_snapshot_date")
            loaded.append({
                "path": path.as_posix(),
                "date": snap_date,
                "date_text": snap_date.isoformat(),
                "payload": payload,
                "station_count": len(stations),
            })
        except Exception as exc:
            skipped.append({"file": path.as_posix(), "reason": str(exc)})

    output: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_snapshot_date": None,
        "days_available": len(files),
        "valid_snapshot_days": len(loaded),
        "skipped_files": skipped,
        "fuel_map": FUEL_MAP,
        "stations": {},
    }

    if len(loaded) < 2:
        output["message"] = "At least two daily snapshots are needed for station history."
        write_json(OUTPUT_FILE, output)
        print(f"Generated {OUTPUT_FILE} with limited data")
        return

    loaded.sort(key=lambda x: x["date"])
    latest = loaded[-1]
    previous = loaded[-2]
    target_7d = latest["date"] - timedelta(days=7)
    seven_day_candidates = [s for s in loaded[:-1] if s["date"] <= target_7d]
    seven_day = seven_day_candidates[-1] if seven_day_candidates else loaded[0]

    output["latest_snapshot_date"] = latest["date_text"]
    output["previous_snapshot_date"] = previous["date_text"]
    output["seven_day_reference_date"] = seven_day["date_text"]
    output["latest_station_count"] = latest["station_count"]

    latest_maps = {mode: price_map(latest["payload"], fuel_key) for mode, fuel_key in FUEL_MAP.items()}
    previous_maps = {mode: price_map(previous["payload"], fuel_key) for mode, fuel_key in FUEL_MAP.items()}
    seven_maps = {mode: price_map(seven_day["payload"], fuel_key) for mode, fuel_key in FUEL_MAP.items()}

    station_ids = set()
    for m in latest_maps.values():
        station_ids.update(m.keys())

    stations: dict[str, Any] = {}
    for sid in sorted(station_ids):
        station_entry: dict[str, Any] = {}
        for mode in FUEL_MAP:
            latest_price = latest_maps[mode].get(sid)
            if latest_price is None:
                continue
            one_day = change_payload(latest_price, previous_maps[mode].get(sid), previous["date_text"])
            seven = change_payload(latest_price, seven_maps[mode].get(sid), seven_day["date_text"])
            if one_day is None and seven is None:
                continue
            station_entry[mode] = {
                "latest_price": latest_price,
                "latest_date": latest["date_text"],
                "change_1d": one_day,
                "change_7d": seven,
            }
        if station_entry:
            stations[sid] = station_entry

    output["stations"] = stations
    output["station_history_count"] = len(stations)

    write_json(OUTPUT_FILE, output)
    print(f"Generated {OUTPUT_FILE}")
    print(f"Station history entries: {len(stations)}")
    print(f"Latest: {latest['date_text']} | Previous: {previous['date_text']} | 7-day ref: {seven_day['date_text']}")


if __name__ == "__main__":
    main()

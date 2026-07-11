#!/usr/bin/env python3

import argparse
import calendar
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LATEST_FILE = ROOT / "data" / "latest.json"
DAILY_DIR = ROOT / "history" / "daily"
MONTHLY_DIR = ROOT / "history" / "monthly"

HISTORY_SUMMARY_FILE = ROOT / "data" / "history-summary.json"
TRENDS_FILE = ROOT / "data" / "trends-30d.json"
TRENDS_STATUS_FILE = ROOT / "data" / "trends-status.json"
RETENTION_STATUS_FILE = ROOT / "data" / "retention-status.json"
STATUS_FILE = ROOT / "data" / "history-status.json"


def read_json(path, errors, label):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        errors.append(f"{label} is missing: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        errors.append(
            f"{label} contains invalid JSON: "
            f"{path.relative_to(ROOT)} ({exc})"
        )
    except OSError as exc:
        errors.append(
            f"{label} cannot be read: "
            f"{path.relative_to(ROOT)} ({exc})"
        )

    return None


def parse_snapshot_date(path):
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def check_monthly_summaries(as_of, errors, warnings):
    paths = sorted(MONTHLY_DIR.glob("????-??.json"))

    result = {
        "files_found": len(paths),
        "valid_files": 0,
        "invalid_files": 0,
        "incomplete_files": 0,
    }

    if not paths:
        warnings.append("No monthly history summaries found.")
        return result

    valid_month_paths = []

    for path in paths:
        payload = read_json(path, errors, f"Monthly summary {path.name}")

        if payload is None:
            result["invalid_files"] += 1
            continue

        expected_month = path.stem

        if payload.get("month") != expected_month:
            errors.append(
                f"Monthly summary month mismatch: {path.name}"
            )
            result["invalid_files"] += 1
            continue

        if payload.get("skipped_files"):
            errors.append(
                f"Monthly summary contains skipped files: {path.name}"
            )
            result["invalid_files"] += 1
            continue

        try:
            month_date = datetime.strptime(expected_month, "%Y-%m").date()
        except ValueError:
            errors.append(f"Invalid monthly summary filename: {path.name}")
            result["invalid_files"] += 1
            continue

        processed = payload.get("snapshot_files_processed", 0)
        expected_days = calendar.monthrange(
            month_date.year,
            month_date.month,
        )[1]

        is_current_month = (
            month_date.year == as_of.year
            and month_date.month == as_of.month
        )

        valid_month_paths.append((path, processed, expected_days, is_current_month))

    if not valid_month_paths:
        return result

    first_month_name = valid_month_paths[0][0].stem

    for path, processed, expected_days, is_current_month in valid_month_paths:
        if processed <= 0:
            errors.append(
                f"Monthly summary has zero processed snapshots: {path.name}"
            )
            result["invalid_files"] += 1
            continue

        if processed != expected_days:
            result["incomplete_files"] += 1

            if is_current_month:
                warnings.append(
                    f"Current month summary is partial: "
                    f"{path.name} ({processed}/{expected_days} days)"
                )
            elif path.stem == first_month_name:
                warnings.append(
                    f"First collection month is partial: "
                    f"{path.name} ({processed}/{expected_days} days)"
                )
            else:
                errors.append(
                    f"Completed month summary is incomplete: "
                    f"{path.name} ({processed}/{expected_days} days)"
                )
                result["invalid_files"] += 1
                continue

        result["valid_files"] += 1

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Check Driverz fuel-history pipeline health."
    )

    parser.add_argument(
        "--as-of",
        help="Override current UTC date for testing, format YYYY-MM-DD.",
    )

    parser.add_argument(
        "--max-snapshot-age-days",
        type=int,
        default=1,
        help="Maximum allowed age of newest daily snapshot.",
    )

    args = parser.parse_args()

    if args.max_snapshot_age_days < 0:
        raise SystemExit("--max-snapshot-age-days must be zero or greater")

    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
        except ValueError:
            raise SystemExit("--as-of must use YYYY-MM-DD")
    else:
        as_of = datetime.now(timezone.utc).date()

    errors = []
    warnings = []

    today_snapshot = DAILY_DIR / f"{as_of.isoformat()}.json"

    if not LATEST_FILE.exists():
        errors.append("data/latest.json is missing.")
    else:
        read_json(LATEST_FILE, errors, "Latest fuel data")

    if not today_snapshot.exists():
        errors.append(
            f"Today snapshot is missing: "
            f"{today_snapshot.relative_to(ROOT)}"
        )

    station_count = 0

    if today_snapshot.exists():
        snapshot = read_json(today_snapshot, errors, "Today snapshot")

        if snapshot is not None:
            station_count = snapshot.get("station_count", 0)

            if station_count <= 0:
                errors.append("Today snapshot has zero stations.")

    snapshot_paths = sorted(DAILY_DIR.glob("????-??-??.json"))
    valid_snapshot_dates = [
        parse_snapshot_date(path)
        for path in snapshot_paths
        if parse_snapshot_date(path) is not None
    ]

    newest_snapshot = None
    newest_snapshot_age_days = None

    if not valid_snapshot_dates:
        errors.append("No valid daily history snapshots found.")
    else:
        newest_snapshot = max(valid_snapshot_dates)
        newest_snapshot_age_days = (as_of - newest_snapshot).days

        if newest_snapshot_age_days < 0:
            errors.append(
                f"Newest snapshot is in the future: {newest_snapshot}"
            )
        elif newest_snapshot_age_days > args.max_snapshot_age_days:
            errors.append(
                f"Newest snapshot is stale: {newest_snapshot} "
                f"({newest_snapshot_age_days} days old)"
            )

    days_available = 0

    trends = read_json(TRENDS_FILE, errors, "Fuel trends")

    if trends is not None:
        days_available = trends.get("days_available", 0)

        if days_available <= 0:
            errors.append("Trend analysis has zero days available.")

        if not trends.get("uk_average", {}):
            warnings.append("No fuel averages found in trends file.")

    read_json(
        TRENDS_STATUS_FILE,
        errors,
        "Trends status",
    )

    history_summary = read_json(
        HISTORY_SUMMARY_FILE,
        errors,
        "History summary",
    )

    history_summary_station_count = 0
    history_summary_latest_station_count = 0
    history_summary_valid_days = 0

    if history_summary is not None:
        if isinstance(history_summary, dict):
            history_summary_station_count = history_summary.get(
                "station_history_count",
                0,
            )

            history_summary_latest_station_count = history_summary.get(
                "latest_station_count",
                0,
            )

            history_summary_valid_days = history_summary.get(
                "valid_snapshot_days",
                0,
            )

            history_summary_skipped_files = history_summary.get(
                "skipped_files",
                [],
            )

            if history_summary_station_count <= 0:
                errors.append(
                    "History summary has zero station history entries."
                )

            if history_summary_latest_station_count <= 0:
                errors.append(
                    "History summary reports zero stations in latest snapshot."
                )

            if history_summary_valid_days < 2:
                errors.append(
                    "History summary has fewer than two valid snapshot days."
                )

            if history_summary_skipped_files:
                warnings.append(
                    f"History summary skipped "
                    f"{len(history_summary_skipped_files)} snapshot file(s)."
                )
        else:
            errors.append("History summary JSON root is not an object.")

    monthly_status = check_monthly_summaries(
        as_of,
        errors,
        warnings,
    )

    retention_status = read_json(
        RETENTION_STATUS_FILE,
        errors,
        "Retention status",
    )

    retention_mode = None
    retention_blocked_count = 0
    retention_deleted_count = 0

    if retention_status is not None:
        retention_mode = retention_status.get("mode")
        retention_blocked_count = retention_status.get("blocked_count", 0)
        retention_deleted_count = retention_status.get("deleted_count", 0)

        if retention_mode not in ("dry-run", "apply"):
            errors.append(
                f"Unknown retention mode: {retention_mode!r}"
            )

        if retention_blocked_count > 0:
            warnings.append(
                f"Retention has {retention_blocked_count} blocked snapshot(s)."
            )

    status = {
        "schema_version": 2,
        "status": "failed" if errors else "success",
        "last_checked_date": as_of.isoformat(),
        "today_snapshot": str(today_snapshot.relative_to(ROOT)),
        "station_count": station_count,
        "daily_snapshot_count": len(snapshot_paths),
        "newest_snapshot": (
            newest_snapshot.isoformat()
            if newest_snapshot is not None
            else None
        ),
        "newest_snapshot_age_days": newest_snapshot_age_days,
        "days_available": days_available,
        "history_summary_station_count": history_summary_station_count,
        "history_summary_latest_station_count": (
            history_summary_latest_station_count
        ),
        "history_summary_valid_days": history_summary_valid_days,
        "monthly_summaries": monthly_status,
        "retention": {
            "mode": retention_mode,
            "blocked_count": retention_blocked_count,
            "deleted_count": retention_deleted_count,
        },
        "errors": errors,
        "warnings": warnings,
    }

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if errors:
        print("Health check failed:")

        for error in errors:
            print(f"- {error}")

        if warnings:
            print("Warnings:")

            for warning in warnings:
                print(f"- {warning}")

        raise SystemExit(1)

    print("Health check passed.")

    if warnings:
        print("Warnings:")

        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()

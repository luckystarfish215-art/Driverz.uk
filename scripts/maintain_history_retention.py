#!/usr/bin/env python3

import argparse
import json
import calendar
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "history" / "daily"
MONTHLY_DIR = ROOT / "history" / "monthly"
STATUS_FILE = ROOT / "data" / "retention-status.json"

DEFAULT_RETENTION_DAYS = 90


def parse_snapshot_date(path):
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_monthly_summary(snapshot_date):
    path = MONTHLY_DIR / f"{snapshot_date:%Y-%m}.json"

    if not path.is_file():
        return False, "missing monthly summary"

    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return False, f"invalid monthly summary: {exc}"

    expected_month = f"{snapshot_date:%Y-%m}"

    if payload.get("month") != expected_month:
        return False, "monthly summary month mismatch"

    if payload.get("skipped_files"):
        return False, "monthly summary contains skipped files"

    expected_days = calendar.monthrange(
        snapshot_date.year,
        snapshot_date.month,
    )[1]

    if payload.get("snapshot_files_processed") != expected_days:
        return False, (
            f"incomplete monthly summary: "
            f"{payload.get('snapshot_files_processed')} of {expected_days} days"
        )

    return True, None


def write_status(payload):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Maintain Driverz daily fuel history retention."
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help="Number of recent calendar days to retain.",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete eligible daily snapshots. Default is dry-run.",
    )

    parser.add_argument(
        "--as-of",
        help="Override current UTC date for testing, format YYYY-MM-DD.",
    )

    args = parser.parse_args()

    if args.retention_days < 1:
        raise SystemExit("--retention-days must be at least 1")

    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
        except ValueError:
            raise SystemExit("--as-of must use YYYY-MM-DD")
    else:
        as_of = datetime.now(timezone.utc).date()

    # A snapshot is eligible when its date is strictly before this cutoff.
    cutoff = as_of - timedelta(days=args.retention_days)

    snapshots = sorted(DAILY_DIR.glob("????-??-??.json"))

    invalid_files = []
    retained_files = []
    eligible_files = []
    blocked_files = []
    deleted_files = []

    for path in snapshots:
        snapshot_date = parse_snapshot_date(path)

        if snapshot_date is None:
            invalid_files.append(path.name)
            continue

        if snapshot_date >= cutoff:
            retained_files.append(path.name)
            continue

        item = {
            "file": path.name,
            "date": snapshot_date.isoformat(),
            "monthly_summary": f"{snapshot_date:%Y-%m}.json",
        }

        summary_valid, block_reason = validate_monthly_summary(snapshot_date)

        if not summary_valid:
            item["reason"] = block_reason
            blocked_files.append(item)
            continue

        eligible_files.append(item)

        if args.apply:
            path.unlink()
            deleted_files.append(item)

    mode = "apply" if args.apply else "dry-run"

    status = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "as_of": as_of.isoformat(),
        "retention_days": args.retention_days,
        "cutoff_date": cutoff.isoformat(),
        "daily_snapshots_found": len(snapshots),
        "retained_count": len(retained_files),
        "eligible_count": len(eligible_files),
        "blocked_count": len(blocked_files),
        "deleted_count": len(deleted_files),
        "invalid_files": invalid_files,
        "eligible_files": eligible_files,
        "blocked_files": blocked_files,
        "deleted_files": deleted_files,
    }

    write_status(status)

    print(f"Mode: {mode}")
    print(f"As of: {as_of}")
    print(f"Retention days: {args.retention_days}")
    print(f"Cutoff: snapshots before {cutoff} are candidates")
    print(f"Daily snapshots found: {len(snapshots)}")
    print(f"Retained: {len(retained_files)}")
    print(f"Eligible: {len(eligible_files)}")
    print(f"Blocked: {len(blocked_files)}")
    print(f"Deleted: {len(deleted_files)}")
    print(f"Status: {STATUS_FILE.relative_to(ROOT)}")

    if blocked_files:
        print()
        print("Blocked snapshots without monthly summaries:")

        for item in blocked_files:
            print(
                f"  {item['file']} -> "
                f"{item.get('reason', 'monthly summary validation failed')}"
            )

    if not args.apply and eligible_files:
        print()
        print("Dry-run only. Eligible snapshots were NOT deleted.")

        for item in eligible_files:
            print(f"  would delete {item['file']}")


if __name__ == "__main__":
    main()

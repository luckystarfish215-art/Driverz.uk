#!/usr/bin/env bash
set -euo pipefail

# Create a small history/data audit zip.
# Usage: scripts/make_history_sample_zip.sh [number_of_daily_files]
# Default: 14 latest daily snapshots.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DAYS="${1:-14}"
OUT_DIR="_audit_exports"
mkdir -p "$OUT_DIR"

python3 - "$DAYS" <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, timezone
import sys

try:
    days = int(sys.argv[1])
except Exception:
    days = 14
if days < 1:
    days = 1
if days > 90:
    days = 90

root = Path.cwd()
out_dir = root / "_audit_exports"
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
out_file = out_dir / f"driverz-history-sample-{days}d-{stamp}.zip"

files = []
for rel in [
    "data/api-sync-status.json",
    "data/latest-status.json",
    "data/history-status.json",
    "data/trends-status.json",
    "data/trends-30d.json",
    "data/history-summary.json",
    "data/costco-fuel-hours.json",
]:
    p = root / rel
    if p.exists() and p.is_file():
        files.append((p, rel))

daily_dir = root / "history" / "daily"
if daily_dir.exists():
    daily_files = sorted(daily_dir.glob("*.json"))[-days:]
    files.extend((p, p.relative_to(root).as_posix()) for p in daily_files)

monthly_dir = root / "history" / "monthly"
if monthly_dir.exists():
    monthly_files = sorted(monthly_dir.glob("*.json"))[-3:]
    files.extend((p, p.relative_to(root).as_posix()) for p in monthly_files)

manifest = [
    "Driverz history sample export",
    f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
    f"Daily snapshots requested: {days}",
    "",
    "Included files:",
]
manifest.extend(rel for _, rel in sorted(files, key=lambda x: x[1]))

with ZipFile(out_file, "w", ZIP_DEFLATED) as z:
    z.writestr("HISTORY_SAMPLE_MANIFEST.txt", "\n".join(manifest) + "\n")
    for path, rel in sorted(files, key=lambda x: x[1]):
        z.write(path, rel)

print(out_file.as_posix())
print(f"Included {len(files)} files")
PY

#!/usr/bin/env bash
set -euo pipefail

# Create a lightweight Driverz audit zip for ChatGPT/code review.
# It excludes large/generated datasets and history snapshots, while keeping
# source code, HTML, CSS, JS, API routes, scripts, sitemap, robots, and small status files.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="_audit_exports"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_FILE="$OUT_DIR/driverz-audit-light-$STAMP.zip"
mkdir -p "$OUT_DIR"

python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, timezone
import os

root = Path.cwd()
out_dir = root / "_audit_exports"
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
out_file = out_dir / f"driverz-audit-light-{stamp}.zip"

exclude_dirs = {
    ".git",
    "node_modules",
    ".vercel",
    "_audit_exports",
    "__pycache__",
}

# Large/generated data should not be included in a normal site audit.
exclude_exact = {
    "data/fuel_data.csv",
    "data/latest.json",
}

exclude_prefixes = (
    "history/daily/",
    "history/monthly/",
)

exclude_suffixes = (
    ".bak",
    ".zip",
    ".log",
    ".tmp",
    ".DS_Store",
)

include_files = []
for path in root.rglob("*"):
    if not path.is_file():
        continue
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts)
    if parts & exclude_dirs:
        continue
    if rel in exclude_exact:
        continue
    if rel.startswith(exclude_prefixes):
        continue
    if rel.endswith(exclude_suffixes):
        continue
    include_files.append((path, rel))

manifest = [
    "Driverz lightweight audit export",
    f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
    "",
    "Excluded:",
    "- .git / node_modules / .vercel",
    "- data/fuel_data.csv",
    "- data/latest.json",
    "- history/daily/*",
    "- history/monthly/*",
    "- *.bak / *.zip / *.log / *.tmp",
    "",
    "Included files:",
]
manifest.extend(rel for _, rel in sorted(include_files, key=lambda x: x[1]))

with ZipFile(out_file, "w", ZIP_DEFLATED) as z:
    z.writestr("AUDIT_EXPORT_MANIFEST.txt", "\n".join(manifest) + "\n")
    for path, rel in sorted(include_files, key=lambda x: x[1]):
        z.write(path, rel)

print(out_file.as_posix())
print(f"Included {len(include_files)} files")
PY

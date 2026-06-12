#!/bin/sh
set -eu

REPO="$HOME/driverz-automation/Driverz.uk"

cd "$REPO"

echo "=== Driverz ESP32 device JSON update started: $(date) ==="

echo "Pull latest repo..."
git pull --rebase origin main

echo "Generate device-demo.json..."
python3 scripts/generate_device_json.py

echo "Generated JSON:"
cat device-demo.json

echo "Check changes..."
if git diff --quiet -- device-demo.json scripts/generate_device_json.py; then
  echo "No device JSON changes to commit."
else
  git add device-demo.json scripts/generate_device_json.py
  git commit -m "Update ESP32 device JSON"

  echo "Pull latest before push..."
  git pull --rebase origin main

  echo "Push to GitHub..."
  git push origin main
fi

echo "=== Driverz ESP32 device JSON update finished: $(date) ==="

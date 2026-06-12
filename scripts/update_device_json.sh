#!/bin/sh
set -eu

REPO="$HOME/driverz-automation/Driverz.uk"

cd "$REPO"

echo "=== Driverz ESP32 device update started: $(date) ==="

echo "Pull latest repo..."
git pull --rebase origin main

echo "Generate lightweight station index..."
python3 scripts/generate_device_station_index.py

echo "Generate ESP32 display JSON..."
python3 scripts/generate_device_json.py

echo "Generated device-demo.json:"
cat device-demo.json

echo "Check changes..."
if git diff --quiet -- device-demo.json device/stations.json scripts/generate_device_json.py scripts/generate_device_station_index.py scripts/update_device_json.sh; then
  echo "No device changes to commit."
else
  git add device-demo.json device/stations.json scripts/generate_device_json.py scripts/generate_device_station_index.py scripts/update_device_json.sh

  git commit -m "Update ESP32 device data"

  echo "Pull latest before push..."
  git pull --rebase origin main

  echo "Push to GitHub..."
  git push origin main
fi

echo "=== Driverz ESP32 device update finished: $(date) ==="

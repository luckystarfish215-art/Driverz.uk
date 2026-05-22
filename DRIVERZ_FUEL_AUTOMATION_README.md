# Driverz.uk Fuel Data Automation

This README documents the current Driverz.uk fuel data workflow using a Synology NAS, GitHub, GitHub Actions, and Vercel.

## Current live workflow

Driverz.uk fuel data is now updated automatically by the Synology NAS.

```text
Synology NAS Task Scheduler
→ GOV Fuel Finder API
→ update data/fuel_data.csv
→ push to GitHub
→ GitHub Action converts CSV to data/latest.json
→ Vercel deploys Driverz.uk
```

The NAS is the main updater. Manual CSV upload is now only a backup method.

---

## Main update methods

### 1. Normal automatic update

The NAS runs the fuel sync script on a schedule.

```text
NAS → GOV Fuel Finder API → data/fuel_data.csv → GitHub → Vercel
```

Recommended schedule:

```text
Morning: 06:30
Afternoon: 16:30
```

The afternoon task can be created by duplicating the morning task in DSM Task Scheduler.

### 2. Manual backup update

If the NAS is off, broken, or the scheduled task fails, you can still manually upload a fresh CSV to GitHub:

```text
GitHub → Driverz.uk repo → data/fuel_data.csv → replace/upload file
```

Then the GitHub Action should regenerate:

```text
data/latest.json
```

---

## Synology NAS location

The Driverz.uk repo is stored on the NAS here:

```bash
/var/services/homes/Mark/driverz-automation/Driverz.uk
```

The private environment file is stored outside the repo:

```bash
/var/services/homes/Mark/driverz-automation/driverz.env
```

Do not upload `driverz.env` to GitHub.

---

## Private environment file

The NAS uses this file:

```bash
~/driverz-automation/driverz.env
```

It contains GOV Fuel Finder API credentials:

```bash
export FUEL_FINDER_CLIENT_ID='your_client_id_here'
export FUEL_FINDER_CLIENT_SECRET='your_client_secret_here'
```

Protect it with:

```bash
chmod 600 ~/driverz-automation/driverz.env
```

---

## Synology Task Scheduler script

Use this script in:

```text
DSM → Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script
```

Recommended task name:

```text
Driverz Fuel API Sync
```

Recommended user:

```text
Mark
```

Recommended script:

```bash
cd /var/services/homes/Mark/driverz-automation/Driverz.uk
git pull --rebase
source /var/services/homes/Mark/driverz-automation/driverz.env
python3 scripts/sync_fuel_from_api.py
git restore data/latest.json
git add data/fuel_data.csv data/api-sync-status.json
git commit -m "Update fuel data from NAS API sync" || true
git pull --rebase
git push
```

Important: `data/latest.json` is restored before committing because GitHub Actions manages that file.

---

## Files to keep

### `.github/workflows/`

Keep:

```text
convert-csv-to-latest.yml
save-history.yml
```

Purpose:

```text
convert-csv-to-latest.yml  Converts data/fuel_data.csv to data/latest.json
save-history.yml           Saves daily history snapshots and trend data
```

Remove or disable old/test workflows:

```text
sync_fuel_api.yml
test-fuel-api.yml
update_fuel.yml
```

These old workflows are no longer needed because GitHub Actions should not call the GOV API directly. GitHub cloud runner IPs may be blocked by GOV Fuel Finder API access rules.

### `scripts/`

Keep:

```text
analyse_fuel_trends.py
check_history_health.py
convert_csv_to_latest.py
save_history_snapshot.py
sync_fuel_from_api.py
```

Purpose:

```text
sync_fuel_from_api.py       NAS production script. Calls GOV API and creates fuel_data.csv.
convert_csv_to_latest.py    GitHub Action script. Converts CSV to latest.json.
save_history_snapshot.py    Saves daily historical data.
analyse_fuel_trends.py      Builds trend/history analysis data.
check_history_health.py     Checks whether the history system is healthy.
```

Remove:

```text
test_fuel_finder_api.py
```

This was only a GOV API test script and is no longer needed in GitHub.

---

## How to check NAS sync status

SSH into the NAS from Mac:

```bash
ssh Mark@192.168.10.100
```

Go to the repo:

```bash
cd ~/driverz-automation/Driverz.uk
```

Check API sync status:

```bash
grep -E '"status"|"finished_at"|"price_records"|"info_records"|"csv_rows"' data/api-sync-status.json
```

Good result should show:

```text
"status": "success"
"finished_at": recent date/time
"price_records": around 7900+
"info_records": around 7900+
"csv_rows": around 7900+
```

Check Git status:

```bash
git status
```

Good result:

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

Check latest commits:

```bash
git log -3 --format="%h %cd %s" --date=local
```

Expected commits may look like:

```text
Update fuel data from NAS API sync
Convert fuel CSV to latest JSON
```

---

## How to check live website status

Open:

```text
https://driverz.uk/data/api-sync-status.json
```

Check:

```text
status = success
finished_at = latest successful sync time
csv_rows = around 7900+
```

Also check:

```text
https://driverz.uk/data/latest.json
```

This is the file used by the website frontend.

---

## GitHub token note

For `git push` from NAS, GitHub requires a Personal Access Token.

Recommended token type:

```text
Fine-grained Personal Access Token
```

Recommended repository access:

```text
Only selected repository: Driverz.uk
```

Required permission:

```text
Repository permissions → Contents → Read and write
Metadata → Read-only
```

The NAS may use:

```bash
git config credential.helper store
```

This lets scheduled tasks push without typing the token each time.

Security warning: this stores the GitHub token on the NAS user account. Only use this on a private trusted NAS account.

---

## Common issues and fixes

### Git push rejected: fetch first

Error:

```text
! [rejected] main -> main (fetch first)
```

Fix:

```bash
git pull --rebase
git push
```

This often happens because GitHub Actions created a new commit after NAS pushed `fuel_data.csv`.

### NAS is ahead of origin by 1 commit

Check:

```bash
git status
```

If it says:

```text
Your branch is ahead of 'origin/main' by 1 commit
```

Run:

```bash
git pull --rebase
git push
```

### `data/latest.json` is modified locally

Because `sync_fuel_from_api.py` can generate `latest.json`, but GitHub Actions should manage it.

Fix:

```bash
git restore data/latest.json
```

Then commit only:

```bash
git add data/fuel_data.csv data/api-sync-status.json
```

### GOV API batch 17 returns 404

This is normal. It means there are no more batches.

Expected behaviour:

```text
batch 17: batch not available. Stopping.
```

The script should continue and complete successfully.

### Vodafone home IP changes

The NAS should usually still work because it calls the API from a UK residential Vodafone IP. If GOV API returns 403 after an IP change, manually upload CSV as backup and test the NAS API again later.

---

## Current strategy

For now:

```text
1. Keep NAS automation stable.
2. Monitor Google Search Console.
3. Let Google index the site.
4. Watch queries, clicks, and impressions.
5. Add more features only when useful.
```

Recommended later feature:

```text
Fuel data history / trend feature
```

Target timing:

```text
Around 1 month after enough history has accumulated.
```

Possible future history features:

```text
Price movement by brand
Station price changes over time
Local cheapest fuel trend
Supermarket vs motorway fuel comparison
Weekly petrol/diesel movement
```

---

## Maintenance checklist

Daily or occasional quick check:

```bash
cd ~/driverz-automation/Driverz.uk
grep -E '"status"|"finished_at"|"price_records"|"info_records"|"csv_rows"' data/api-sync-status.json
git status
git log -3 --format="%h %cd %s" --date=local
```

Good state:

```text
status = success
finished_at = recent
csv_rows = around 7900+
working tree clean
latest commit includes NAS sync and/or CSV conversion
```

---

## Final note

Do not commit or upload:

```text
driverz.env
GOV API credentials
GitHub token
```

The production automation should only commit:

```text
data/fuel_data.csv
data/api-sync-status.json
```

GitHub Actions should manage:

```text
data/latest.json
```

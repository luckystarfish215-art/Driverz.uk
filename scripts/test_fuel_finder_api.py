import json
import os
import urllib.request
import urllib.error

CLIENT_ID = os.environ.get("FUEL_FINDER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_FINDER_CLIENT_SECRET")
TOKEN_URL = os.environ.get("FUEL_FINDER_TOKEN_URL")
PRICES_URL = os.environ.get("FUEL_FINDER_PFS_PRICES_URL")
INFO_URL = os.environ.get("FUEL_FINDER_PFS_INFO_URL")

def fail(message):
    raise SystemExit(message)

def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Driverz.uk API test contact: mtamtc76@gmail.com",
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"Token request failed with HTTP {exc.code}")
        print("Response headers:")
        print(exc.headers)
        print("Response preview:")
        print(error_body[:1000])
        raise

def get_json(url, token, label):
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Driverz.uk API test contact: mtamtc76@gmail.com",
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"{label} request failed with HTTP {exc.code}")
        print("Response headers:")
        print(exc.headers)
        print("Response preview:")
        print(error_body[:1000])
        raise

for name, value in {
    "FUEL_FINDER_CLIENT_ID": CLIENT_ID,
    "FUEL_FINDER_CLIENT_SECRET": CLIENT_SECRET,
    "FUEL_FINDER_TOKEN_URL": TOKEN_URL,
    "FUEL_FINDER_PFS_PRICES_URL": PRICES_URL,
    "FUEL_FINDER_PFS_INFO_URL": INFO_URL,
}.items():
    if not value:
        fail(f"Missing GitHub secret: {name}")

print("All required secrets found.")
print("Requesting token using JSON body...")

token_payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}

status, token_response = post_json(TOKEN_URL, token_payload)

print(f"Token request status: {status}")

token_json = json.loads(token_response)
access_token = token_json.get("access_token")

if not access_token:
    print("Token response:")
    print(json.dumps(token_json, indent=2)[:1000])
    fail("No access_token found.")

print("Access token received successfully.")

print("Testing PFS prices API...")
status, prices_response = get_json(PRICES_URL, access_token, "Prices API")
print(f"Prices API status: {status}")
print("Prices API response preview:")
print(prices_response[:1000])

print("Testing PFS info API...")
status, info_response = get_json(INFO_URL, access_token, "PFS info API")
print(f"PFS info API status: {status}")
print("PFS info API response preview:")
print(info_response[:1000])

print("Fuel Finder API test completed.")

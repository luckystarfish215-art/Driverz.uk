import json
import os
import urllib.parse
import urllib.request
import urllib.error

CLIENT_ID = os.environ.get("FUEL_FINDER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_FINDER_CLIENT_SECRET")
TOKEN_URL = os.environ.get("FUEL_FINDER_TOKEN_URL")
PRICES_URL = os.environ.get("FUEL_FINDER_PFS_PRICES_URL")
INFO_URL = os.environ.get("FUEL_FINDER_PFS_INFO_URL")

def fail(message):
    raise SystemExit(message)

def post_form(url, payload):
    body = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
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
        print("Response preview:")
        print(error_body[:1000])
        raise

if not CLIENT_ID:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_ID")

if not CLIENT_SECRET:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_SECRET")

if not TOKEN_URL:
    fail("Missing GitHub secret: FUEL_FINDER_TOKEN_URL")

if not PRICES_URL:
    fail("Missing GitHub secret: FUEL_FINDER_PFS_PRICES_URL")

if not INFO_URL:
    fail("Missing GitHub secret: FUEL_FINDER_PFS_INFO_URL")

print("Client ID found.")
print("Client secret found.")
print("Token URL found.")
print("Prices URL found.")
print("PFS info URL found.")
print("Requesting token using form-urlencoded body...")

token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read"
}

status, token_response = post_form(TOKEN_URL, token_payload)

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

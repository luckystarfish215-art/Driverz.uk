import json
import os
import urllib.parse
import urllib.request
import urllib.error

CLIENT_ID = os.environ.get("FUEL_FINDER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_FINDER_CLIENT_SECRET")

TOKEN_URL = "https://www.fuel-finder.service.gov.uk/api/v1/oauth/generate_access_token"
PRICES_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices"

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

def get_json(url, token):
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
        print(f"API request failed with HTTP {exc.code}")
        print("Response preview:")
        print(error_body[:1000])
        raise

if not CLIENT_ID:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_ID")

if not CLIENT_SECRET:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_SECRET")

print("Client ID found.")
print("Client secret found.")
print("Requesting token using form-urlencoded body...")

token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read"
}

status, token_response = post_form(TOKEN_URL, token_payload)

print(f"Token request status: {status}")

try:
    token_json = json.loads(token_response)
except json.JSONDecodeError:
    print("Token response was not JSON:")
    print(token_response[:1000])
    raise

access_token = token_json.get("access_token")

if not access_token:
    print("Token response:")
    print(json.dumps(token_json, indent=2)[:1000])
    fail("No access_token found.")

print("Access token received successfully.")
print("Testing prices API...")

status, api_response = get_json(PRICES_URL, access_token)

print(f"Prices API status: {status}")
print("API response preview:")
print(api_response[:1000])

print("Fuel Finder API test completed.")

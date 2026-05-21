import json
import os
import urllib.parse
import urllib.request
import urllib.error

CLIENT_ID = os.environ.get("FUEL_FINDER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_FINDER_CLIENT_SECRET")

# Based on public examples from Fuel Finder integrations.
# If the official portal gives you different URLs, replace these.
TOKEN_URL = "https://www.developer.fuel-finder.service.gov.uk/api/v1/oauth/generate_access_token"
PFS_URL = "https://www.developer.fuel-finder.service.gov.uk/api/v1/pfs"
PRICES_URL = "https://www.developer.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices"

def fail(message):
    raise SystemExit(message)

def post_form(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Driverz.uk Fuel Finder API test"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"Token request failed with HTTP {exc.code}")
        print(error_body[:1000])
        raise
    except Exception as exc:
        print(f"Token request failed: {exc}")
        raise

def get_json(url, token):
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Driverz.uk Fuel Finder API test"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"API request failed with HTTP {exc.code}")
        print(error_body[:1000])
        raise
    except Exception as exc:
        print(f"API request failed: {exc}")
        raise

if not CLIENT_ID:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_ID")

if not CLIENT_SECRET:
    fail("Missing GitHub secret: FUEL_FINDER_CLIENT_SECRET")

print("Client ID found in GitHub Secrets.")
print("Client secret found in GitHub Secrets.")

token_data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read"
}

status, token_response = post_form(TOKEN_URL, token_data)

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
    fail("No access_token found in token response.")

print("Access token received successfully.")

# Test a small public API request.
# If this endpoint needs pagination/query params, the response will tell us.
status, api_response = get_json(PRICES_URL, access_token)

print(f"Prices API status: {status}")
print("API response preview:")
print(api_response[:1000])

print("Fuel Finder API test completed.")

import os
import re
import requests
from dotenv import load_dotenv # type: ignore

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=ENV_PATH)

API_KEY = os.getenv("ETSY_API_KEY")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID")
BASE_URL = "https://openapi.etsy.com/v3"

ACCESS_TOKEN = os.getenv("ETSY_ACCESS_TOKEN")

def get_headers():
    return {
        "x-api-key": f"{API_KEY}:{SHARED_SECRET}",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

def refresh_access_token():
    global ACCESS_TOKEN
    refresh_token = os.getenv("ETSY_REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError("No ETSY_REFRESH_TOKEN in .env — run auth.py + get_token.py to authenticate.")

    response = requests.post(
        "https://api.etsy.com/v3/public/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": API_KEY,
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    tokens = response.json()

    ACCESS_TOKEN = tokens["access_token"]
    new_refresh_token = tokens["refresh_token"]

    # Write updated tokens back to .env so they persist for future runs
    with open(ENV_PATH, "r") as f:
        env_contents = f.read()

    env_contents = re.sub(r"ETSY_ACCESS_TOKEN=.*", f"ETSY_ACCESS_TOKEN={ACCESS_TOKEN}", env_contents)
    env_contents = re.sub(r"ETSY_REFRESH_TOKEN=.*", f"ETSY_REFRESH_TOKEN={new_refresh_token}", env_contents)

    with open(ENV_PATH, "w") as f:
        f.write(env_contents)

    os.environ["ETSY_REFRESH_TOKEN"] = new_refresh_token
    print("Access token refreshed automatically.")

def api_get(url, params=None):
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 401:
        refresh_access_token()
        response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()

def get_ledger_entries(limit=100, offset=0, min_created=None, max_created=None):
    url = f"{BASE_URL}/application/shops/{SHOP_ID}/payment-account/ledger-entries"
    params = {"limit": limit, "offset": offset}
    if min_created:
        params["min_created"] = min_created
    if max_created:
        params["max_created"] = max_created
    return api_get(url, params)

def get_shop_receipts(limit=100, offset=0, min_created=None, max_created=None):
    url = f"{BASE_URL}/application/shops/{SHOP_ID}/receipts"
    params = {"limit": limit, "offset": offset, "was_paid": True}
    if min_created:
        params["min_created"] = min_created
    if max_created:
        params["max_created"] = max_created
    return api_get(url, params)

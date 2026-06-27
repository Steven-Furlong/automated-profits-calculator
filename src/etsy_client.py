import os
import requests
from dotenv import load_dotenv # type: ignore

load_dotenv()

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

def get_shop_receipts(limit=100, offset=0):
    url = f"{BASE_URL}/application/shops/{SHOP_ID}/receipts"
    params = {
        "limit": limit,
        "offset": offset,
        "was_paid": True
    }
    response = requests.get(url, headers=get_headers(), params=params)
    print(response.json())
    response.raise_for_status()
    return response.json()


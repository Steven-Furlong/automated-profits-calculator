import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY = os.getenv("ETSY_API_KEY")
REDIRECT_URI = os.getenv("ETSY_REDIRECT_URI")

with open("verifier.tmp", "r") as f:
    CODE_VERIFIER = f.read().strip()

AUTH_CODE = input("Paste auth code: ").strip()

response = requests.post(
    "https://api.etsy.com/v3/public/oauth/token",
    data={
        "grant_type": "authorization_code",
        "client_id": API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": AUTH_CODE,
        "code_verifier": CODE_VERIFIER,
    }
)

print(response.status_code)
print(response.json())

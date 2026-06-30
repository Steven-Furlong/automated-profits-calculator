import os
import re
import requests
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=ENV_PATH)

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
response.raise_for_status()
tokens = response.json()

access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

with open(ENV_PATH, "r") as f:
    env_contents = f.read()

if "ETSY_ACCESS_TOKEN=" in env_contents:
    env_contents = re.sub(r"ETSY_ACCESS_TOKEN=.*", f"ETSY_ACCESS_TOKEN={access_token}", env_contents)
else:
    env_contents += f"\nETSY_ACCESS_TOKEN={access_token}"

if "ETSY_REFRESH_TOKEN=" in env_contents:
    env_contents = re.sub(r"ETSY_REFRESH_TOKEN=.*", f"ETSY_REFRESH_TOKEN={refresh_token}", env_contents)
else:
    env_contents += f"\nETSY_REFRESH_TOKEN={refresh_token}"

with open(ENV_PATH, "w") as f:
    f.write(env_contents)

print("Tokens saved to .env successfully.")

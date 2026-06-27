import os
import webbrowser
import urllib.parse
import hashlib
import base64
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY = os.getenv("ETSY_API_KEY")
REDIRECT_URI = os.getenv("ETSY_REDIRECT_URI")

auth_code = None

code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()

with open("verifier.tmp", "w") as f:
    f.write(code_verifier)

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Auth complete! Return to your terminal.")

    def log_message(self, format, *args):
        pass

def get_auth_code():
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": API_KEY,
        "redirect_uri": REDIRECT_URI,
        "scope": "transactions_r billing_r",
        "state": "profit_calc",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    })
    url = f"https://www.etsy.com/oauth/connect?{params}"
    print("Opening browser for Etsy authorization...")
    webbrowser.open(url)
    server = HTTPServer(("localhost", 3003), CallbackHandler)
    server.handle_request()
    return auth_code

if __name__ == "__main__":
    code = get_auth_code()
    print(f"Auth code: {code}")
    print(f"Code verifier saved to verifier.tmp")

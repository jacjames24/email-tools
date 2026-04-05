"""
Run this once to generate Drive tokens for each account.
A browser window will open for each account asking you to grant Drive access.
"""
import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDENTIALS_PATH = r"C:\Users\jacja\Downloads\API Keys\client_secret_346514819391-k9oh1pm26nulrcan17qc9nlhtcq4ui4p.apps.googleusercontent.com.json"

ACCOUNTS = [
    {"name": "Personal", "token": r"C:\Users\jacja\Downloads\API Keys\token_personal_drive.json"},
    {"name": "Freelance", "token": r"C:\Users\jacja\Downloads\API Keys\token_freelance_drive.json"},
]

for account in ACCOUNTS:
    print(f"\nAuthenticating {account['name']} account...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(account["token"], "w") as f:
        f.write(creds.to_json())
    print(f"✓ Token saved: {account['token']}")

print("\nAll accounts authenticated!")

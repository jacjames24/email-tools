import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = r"C:\Users\jacja\Downloads\API Keys\client_secret_346514819391-k9oh1pm26nulrcan17qc9nlhtcq4ui4p.apps.googleusercontent.com.json"
TOKEN_PATH = r"C:\Users\jacja\Downloads\API Keys\token.json"


def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


def get_emails(service, days=30):
    after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"is:unread after:{after}"
    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])
    return messages


def fetch_email_details(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="metadata",
                                         metadataHeaders=["From", "Subject", "Date"]).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    snippet = msg.get("snippet", "")
    return {
        "id": msg_id,
        "from": headers.get("From", "Unknown"),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "snippet": snippet[:100] + "..." if len(snippet) > 100 else snippet,
        "labels": msg.get("labelIds", []),
    }


def is_important(email):
    important_labels = {"IMPORTANT", "STARRED", "CATEGORY_PRIMARY"}
    return bool(important_labels & set(email["labels"]))


def mark_as_read(service, msg_ids):
    if not msg_ids:
        return
    service.users().messages().batchModify(
        userId="me",
        body={"ids": msg_ids, "removeLabelIds": ["UNREAD"]}
    ).execute()


def main():
    print("Authenticating with Gmail...")
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)

    print("Fetching unread emails from the past 30 days...\n")
    messages = get_emails(service, days=30)

    if not messages:
        print("No unread emails found in the past 30 days.")
        return

    print(f"Found {len(messages)} unread email(s). Fetching details...\n")

    emails = []
    for msg in messages:
        details = fetch_email_details(service, msg["id"])
        emails.append(details)

    # Separate important vs rest
    important = [e for e in emails if is_important(e)]
    others = [e for e in emails if not is_important(e)]

    print("=" * 70)
    print(f"IMPORTANT / PRIMARY ({len(important)} emails)")
    print("=" * 70)
    for i, e in enumerate(important, 1):
        print(f"\n[{i}] From:    {e['from']}")
        print(f"    Subject: {e['subject']}")
        print(f"    Date:    {e['date']}")
        print(f"    Preview: {e['snippet']}")

    if others:
        print(f"\n{'=' * 70}")
        print(f"OTHER UNREAD ({len(others)} emails)")
        print("=" * 70)
        for i, e in enumerate(others, 1):
            print(f"\n[{i}] From:    {e['from']}")
            print(f"    Subject: {e['subject']}")
            print(f"    Date:    {e['date']}")
            print(f"    Preview: {e['snippet']}")

    print("\n" + "=" * 70)
    print("Mark emails as read?")
    print("  [1] Mark all as read")
    print("  [2] Mark only important/primary as read")
    print("  [3] Don't mark anything")
    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        all_ids = [e["id"] for e in emails]
        mark_as_read(service, all_ids)
        print(f"Marked {len(all_ids)} emails as read.")
    elif choice == "2":
        imp_ids = [e["id"] for e in important]
        if imp_ids:
            mark_as_read(service, imp_ids)
            print(f"Marked {len(imp_ids)} important emails as read.")
        else:
            print("No important emails to mark.")
    else:
        print("No emails marked as read.")


if __name__ == "__main__":
    main()

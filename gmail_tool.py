import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

import os
import json
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = r"C:\Users\jacja\Downloads\API Keys\client_secret_346514819391-k9oh1pm26nulrcan17qc9nlhtcq4ui4p.apps.googleusercontent.com.json"

ACCOUNTS = [
    {"name": "Personal", "token": r"C:\Users\jacja\Downloads\API Keys\token_personal.json"},
    {"name": "Freelance", "token": r"C:\Users\jacja\Downloads\API Keys\token_freelance.json"},
]


def authenticate(token_path):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds


def get_emails(service, days=30, unread_only=True):
    after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"after:{after}"
    if unread_only:
        query = "is:unread " + query
    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])
    return messages


def extract_body(payload):
    """Recursively extract plain text body from a message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = extract_body(part)
        if result:
            return result
    return "(No plain text body found)"


def fetch_full_email(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = extract_body(msg["payload"])
    return {
        "from": headers.get("From", "Unknown"),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "body": body,
    }


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


def select_account():
    print("\nSelect account:")
    for i, acc in enumerate(ACCOUNTS, 1):
        print(f"  [{i}] {acc['name']}")
    while True:
        choice = input("Enter choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(ACCOUNTS):
            return ACCOUNTS[int(choice) - 1]
        print("Invalid choice, try again.")


def prompt_active_account():
    print("\nWhich account would you like to use?")
    return select_account()


def get_service(account):
    creds = authenticate(account["token"])
    return build("gmail", "v1", credentials=creds)


def get_own_email(service):
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]


def compose_and_send(service, to=None, subject=None, thread_id=None, in_reply_to=None):
    if to is None:
        to = input("To: ").strip()
    if subject is None:
        subject = input("Subject: ").strip()
    print("Body (type END on a new line to finish):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    service.users().messages().send(userId="me", body=payload).execute()
    print("Email sent.")


def send_flow(account):
    service = get_service(account)
    print(f"\nComposing new email from {account['name']}...")
    compose_and_send(service)


def reply_flow(account):
    service = get_service(account)

    print(f"\nFetching recent emails for {account['name']}...")
    messages = get_emails(service, days=30)
    if not messages:
        print("No recent emails to reply to.")
        return

    emails = [fetch_email_details(service, m["id"]) for m in messages[:10]]

    print("\nSelect an email to reply to:")
    for i, e in enumerate(emails, 1):
        print(f"  [{i}] {e['from']} — {e['subject']}")

    while True:
        choice = input("Enter choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(emails):
            break
        print("Invalid choice, try again.")

    selected = emails[int(choice) - 1]

    # Fetch full message to get Message-ID header for threading
    full_msg = service.users().messages().get(
        userId="me", id=selected["id"], format="metadata",
        metadataHeaders=["From", "Subject", "Message-ID"]
    ).execute()
    headers = {h["name"]: h["value"] for h in full_msg["payload"]["headers"]}
    message_id = headers.get("Message-ID", "")
    sender = headers.get("From", "")

    print(f"\nReplying to: {sender}")
    subject = "Re: " + selected["subject"].lstrip("Re: ")
    compose_and_send(service, to=sender, subject=subject,
                     thread_id=full_msg["threadId"], in_reply_to=message_id)


def delete_flow(account):
    service = get_service(account)

    page_size_input = input("\nEmails per page (default 20): ").strip()
    page_size = int(page_size_input) if page_size_input.isdigit() and int(page_size_input) > 0 else 20

    print(f"\nFetching recent emails for {account['name']}...")
    messages = get_emails(service, days=30)
    if not messages:
        print("No recent emails found.")
        return

    emails = [fetch_email_details(service, m["id"]) for m in messages]
    total = len(emails)
    page = 0
    selected_ids = {}  # id -> subject

    while True:
        start = page * page_size
        end = min(start + page_size, total)
        page_emails = emails[start:end]
        total_pages = (total + page_size - 1) // page_size

        print(f"\nPage {page + 1}/{total_pages}  ({total} emails total)")
        print("-" * 70)
        for i, e in enumerate(page_emails, start + 1):
            marker = " [SELECTED]" if e["id"] in selected_ids else ""
            print(f"  [{i}] {e['from']} — {e['subject']}{marker}")

        print(f"\nSelected for trash: {len(selected_ids)}")
        print("Enter number(s) to toggle selection (e.g. 1 3 5),")
        nav = []
        if page > 0:
            nav.append("[P] Prev")
        if end < total:
            nav.append("[N] Next")
        nav.append("[D] Trash selected")
        nav.append("[Q] Cancel")
        print("  " + "  ".join(nav))
        cmd = input(">> ").strip().lower()

        if cmd == "n" and end < total:
            page += 1
        elif cmd == "p" and page > 0:
            page -= 1
        elif cmd == "d":
            if not selected_ids:
                print("No emails selected.")
                continue
            print(f"\nAbout to trash {len(selected_ids)} email(s):")
            for subj in selected_ids.values():
                print(f"  - {subj}")
            confirm = input("Confirm? (y/n): ").strip().lower()
            if confirm == "y":
                for msg_id in selected_ids:
                    service.users().messages().trash(userId="me", id=msg_id).execute()
                print(f"Moved {len(selected_ids)} email(s) to trash.")
            else:
                print("Cancelled.")
            break
        elif cmd == "q":
            print("Cancelled.")
            break
        else:
            # Parse number selections
            tokens = cmd.split()
            for token in tokens:
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < total:
                        e = emails[idx]
                        if e["id"] in selected_ids:
                            del selected_ids[e["id"]]
                        else:
                            selected_ids[e["id"]] = e["subject"]


def process_account(account, page_size=20, unread_only=True):
    print(f"\n{'=' * 70}")
    print(f"ACCOUNT: {account['name']}")
    print(f"{'=' * 70}")
    print("Authenticating...")
    creds = authenticate(account["token"])
    service = build("gmail", "v1", credentials=creds)

    label = "unread " if unread_only else ""
    print(f"Fetching {label}emails from the past 30 days...\n")
    messages = get_emails(service, days=30, unread_only=unread_only)

    if not messages:
        print("No unread emails found.")
        return

    print(f"Found {len(messages)} unread email(s). Fetching details...\n")
    emails = [fetch_email_details(service, m["id"]) for m in messages]

    # Sort: important first, then others
    important_set = {e["id"] for e in emails if is_important(e)}
    emails_sorted = [e for e in emails if e["id"] in important_set] + \
                    [e for e in emails if e["id"] not in important_set]

    total = len(emails_sorted)
    page = 0

    while True:
        start = page * page_size
        end = min(start + page_size, total)
        page_emails = emails_sorted[start:end]
        total_pages = (total + page_size - 1) // page_size

        print(f"\nPage {page + 1}/{total_pages}  ({total} emails total)")
        print("-" * 70)
        for i, e in enumerate(page_emails, start + 1):
            tag = " [IMPORTANT]" if e["id"] in important_set else ""
            print(f"\n[{i}]{tag}")
            print(f"    From:    {e['from']}")
            print(f"    Subject: {e['subject']}")
            print(f"    Date:    {e['date']}")
            print(f"    Preview: {e['snippet']}")

        nav = []
        if page > 0:
            nav.append("[P] Prev")
        if end < total:
            nav.append("[N] Next")
        nav.append("[Q] Done")
        print("\n  " + "  ".join(nav))
        print("  Or enter a number to read the full email.")
        cmd = input(">> ").strip().lower()

        if cmd == "n" and end < total:
            page += 1
        elif cmd == "p" and page > 0:
            page -= 1
        elif cmd == "q":
            break
        elif cmd.isdigit() and 1 <= int(cmd) <= total:
            idx = int(cmd) - 1
            print(f"\nFetching full email...")
            full = fetch_full_email(service, emails_sorted[idx]["id"])
            print(f"\n{'=' * 70}")
            print(f"From:    {full['from']}")
            print(f"To:      {full['to']}")
            print(f"Subject: {full['subject']}")
            print(f"Date:    {full['date']}")
            print(f"{'=' * 70}\n")
            print(full["body"])
            print(f"\n{'=' * 70}")
            input("Press Enter to go back...")

    print("\nMark emails as read?")
    print("  [1] Mark all as read")
    print("  [2] Mark only important/primary as read")
    print("  [3] Don't mark anything")
    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        mark_as_read(service, [e["id"] for e in emails])
        print(f"Marked {len(emails)} emails as read.")
    elif choice == "2":
        imp_ids = list(important_set)
        if imp_ids:
            mark_as_read(service, imp_ids)
            print(f"Marked {len(imp_ids)} important emails as read.")
        else:
            print("No important emails to mark.")
    else:
        print("No emails marked as read.")


def search_flow(account):
    service = get_service(account)

    print("\nSearch emails (leave any field blank to skip):")
    keyword = input("Keyword (subject/body): ").strip()
    sender  = input("From (sender email): ").strip()
    after   = input("After date (YYYY/MM/DD): ").strip()
    before  = input("Before date (YYYY/MM/DD): ").strip()

    query_parts = []
    if keyword:
        query_parts.append(keyword)
    if sender:
        query_parts.append(f"from:{sender}")
    if after:
        query_parts.append(f"after:{after}")
    if before:
        query_parts.append(f"before:{before}")

    if not query_parts:
        print("No search criteria entered.")
        return

    query = " ".join(query_parts)
    print(f"\nSearching for: {query}")
    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No emails found.")
        return

    print(f"Found {len(messages)} email(s). Fetching details...")
    emails = [fetch_email_details(service, m["id"]) for m in messages]

    page_size_input = input("Emails per page (default 20): ").strip()
    page_size = int(page_size_input) if page_size_input.isdigit() and int(page_size_input) > 0 else 20

    total = len(emails)
    page = 0

    while True:
        start = page * page_size
        end = min(start + page_size, total)
        page_emails = emails[start:end]
        total_pages = (total + page_size - 1) // page_size

        print(f"\nPage {page + 1}/{total_pages}  ({total} results)")
        print("-" * 70)
        for i, e in enumerate(page_emails, start + 1):
            print(f"\n[{i}]")
            print(f"    From:    {e['from']}")
            print(f"    Subject: {e['subject']}")
            print(f"    Date:    {e['date']}")
            print(f"    Preview: {e['snippet']}")

        nav = []
        if page > 0:
            nav.append("[P] Prev")
        if end < total:
            nav.append("[N] Next")
        nav.append("[Q] Done")
        print("\n  " + "  ".join(nav))
        print("  Or enter a number to read the full email.")
        cmd = input(">> ").strip().lower()

        if cmd == "n" and end < total:
            page += 1
        elif cmd == "p" and page > 0:
            page -= 1
        elif cmd == "q":
            break
        elif cmd.isdigit() and 1 <= int(cmd) <= total:
            idx = int(cmd) - 1
            print("\nFetching full email...")
            full = fetch_full_email(service, emails[idx]["id"])
            print(f"\n{'=' * 70}")
            print(f"From:    {full['from']}")
            print(f"To:      {full['to']}")
            print(f"Subject: {full['subject']}")
            print(f"Date:    {full['date']}")
            print(f"{'=' * 70}\n")
            print(full["body"])
            print(f"\n{'=' * 70}")
            input("Press Enter to go back...")


def main():
    active = prompt_active_account()

    while True:
        print("\n" + "=" * 70)
        print(f"GMAIL TOOL  |  Active: {active['name']}")
        print("=" * 70)
        print("  [1] Read emails")
        print("  [2] Compose new email")
        print("  [3] Reply to an email")
        print("  [4] Delete an email")
        print("  [5] Search emails")
        print("  [6] Switch account")
        print("  [7] Exit")
        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            print("\nWhat emails to show?")
            print("  [1] Unread only")
            print("  [2] All emails")
            filter_choice = input("Enter choice (default 1): ").strip()
            unread_only = filter_choice != "2"
            page_size_input = input("Emails per page (default 20): ").strip()
            page_size = int(page_size_input) if page_size_input.isdigit() and int(page_size_input) > 0 else 20
            process_account(active, page_size, unread_only)
        elif choice == "2":
            send_flow(active)
        elif choice == "3":
            reply_flow(active)
        elif choice == "4":
            delete_flow(active)
        elif choice == "5":
            search_flow(active)
        elif choice == "6":
            active = prompt_active_account()
        elif choice == "7":
            break


if __name__ == "__main__":
    main()

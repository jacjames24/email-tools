import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

import json
from mcp.server.fastmcp import FastMCP
from gmail_tool import (
    ACCOUNTS,
    authenticate,
    get_emails,
    fetch_email_details,
    fetch_full_email,
    compose_and_send,
    mark_as_read,
    is_important,
)
from googleapiclient.discovery import build

mcp = FastMCP("Gmail Assistant")


def _get_service(account_name: str):
    account = next((a for a in ACCOUNTS if a["name"].lower() == account_name.lower()), None)
    if not account:
        raise ValueError(f"Unknown account '{account_name}'. Available: {[a['name'] for a in ACCOUNTS]}")
    creds = authenticate(account["token"])
    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def list_emails(account: str = "Personal", days: int = 30, unread_only: bool = True, max_results: int = 20) -> str:
    """
    List emails from a Gmail account.

    Args:
        account: Account name — "Personal" or "Freelance"
        days: How many days back to fetch (default 30)
        unread_only: If True, only fetch unread emails (default True)
        max_results: Maximum number of emails to return (default 20)
    """
    service = _get_service(account)
    messages = get_emails(service, days=days, unread_only=unread_only)
    if not messages:
        return json.dumps({"account": account, "emails": [], "total": 0})

    emails = [fetch_email_details(service, m["id"]) for m in messages[:max_results]]
    for e in emails:
        e["important"] = is_important(e)

    return json.dumps({"account": account, "emails": emails, "total": len(emails)}, indent=2)


@mcp.tool()
def get_email(account: str, email_id: str) -> str:
    """
    Get the full content of an email.

    Args:
        account: Account name — "Personal" or "Freelance"
        email_id: The email ID to retrieve
    """
    service = _get_service(account)
    full = fetch_full_email(service, email_id)
    return json.dumps(full, indent=2)


@mcp.tool()
def send_email(account: str, to: str, subject: str, body: str, html: bool = False) -> str:
    """
    Send an email from a Gmail account.

    Args:
        account: Account name — "Personal" or "Freelance"
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text or HTML)
        html: If True, send as HTML email (default False)
    """
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    service = _get_service(account)

    if html:
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
    else:
        msg = MIMEText(body)
        msg["To"] = to
        msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return json.dumps({"status": "sent", "to": to, "subject": subject})


@mcp.tool()
def reply_to_email(account: str, email_id: str, body: str) -> str:
    """
    Reply to an email.

    Args:
        account: Account name — "Personal" or "Freelance"
        email_id: The email ID to reply to
        body: Reply body (plain text)
    """
    import base64
    from email.mime.text import MIMEText

    service = _get_service(account)

    full_msg = service.users().messages().get(
        userId="me", id=email_id, format="metadata",
        metadataHeaders=["From", "Subject", "Message-ID"]
    ).execute()
    headers = {h["name"]: h["value"] for h in full_msg["payload"]["headers"]}
    sender = headers.get("From", "")
    subject = "Re: " + headers.get("Subject", "").lstrip("Re: ")
    message_id = headers.get("Message-ID", "")
    thread_id = full_msg["threadId"]

    msg = MIMEText(body)
    msg["To"] = sender
    msg["Subject"] = subject
    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me", body={"raw": raw, "threadId": thread_id}
    ).execute()

    return json.dumps({"status": "sent", "to": sender, "subject": subject})


@mcp.tool()
def delete_email(account: str, email_id: str) -> str:
    """
    Move an email to trash.

    Args:
        account: Account name — "Personal" or "Freelance"
        email_id: The email ID to delete
    """
    service = _get_service(account)
    service.users().messages().trash(userId="me", id=email_id).execute()
    return json.dumps({"status": "trashed", "email_id": email_id})


@mcp.tool()
def search_emails(
    account: str,
    keyword: str = "",
    sender: str = "",
    after: str = "",
    before: str = "",
    max_results: int = 20
) -> str:
    """
    Search emails in a Gmail account.

    Args:
        account: Account name — "Personal" or "Freelance"
        keyword: Search keyword (matches subject and body)
        sender: Filter by sender email address
        after: Only emails after this date (YYYY/MM/DD)
        before: Only emails before this date (YYYY/MM/DD)
        max_results: Maximum number of results to return (default 20)
    """
    service = _get_service(account)

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
        return json.dumps({"error": "Please provide at least one search criterion."})

    query = " ".join(query_parts)
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    if not messages:
        return json.dumps({"account": account, "query": query, "emails": [], "total": 0})

    emails = [fetch_email_details(service, m["id"]) for m in messages]
    return json.dumps({"account": account, "query": query, "emails": emails, "total": len(emails)}, indent=2)


@mcp.tool()
def mark_emails_as_read(account: str, email_ids: list[str]) -> str:
    """
    Mark one or more emails as read.

    Args:
        account: Account name — "Personal" or "Freelance"
        email_ids: List of email IDs to mark as read
    """
    service = _get_service(account)
    mark_as_read(service, email_ids)
    return json.dumps({"status": "marked_as_read", "count": len(email_ids)})


if __name__ == "__main__":
    mcp.run()

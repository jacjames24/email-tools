import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

import os
import io
import json
import base64
from mcp.server.fastmcp import FastMCP, Image
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_PATH = r"C:\Users\jacja\Downloads\API Keys\client_secret_346514819391-k9oh1pm26nulrcan17qc9nlhtcq4ui4p.apps.googleusercontent.com.json"

ACCOUNTS = [
    {"name": "Personal", "token": r"C:\Users\jacja\Downloads\API Keys\token_personal_drive.json"},
    {"name": "Freelance", "token": r"C:\Users\jacja\Downloads\API Keys\token_freelance_drive.json"},
]

mcp = FastMCP("Google Drive Assistant")


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


def _get_service(account_name: str):
    account = next((a for a in ACCOUNTS if a["name"].lower() == account_name.lower()), None)
    if not account:
        raise ValueError(f"Unknown account '{account_name}'. Available: {[a['name'] for a in ACCOUNTS]}")
    creds = authenticate(account["token"])
    return build("drive", "v3", credentials=creds)


@mcp.tool()
def list_drive_files(account: str = "Personal", folder_id: str = "root", max_results: int = 50) -> str:
    """
    List files and folders in a Google Drive folder.

    Args:
        account: Account name — "Personal" or "Freelance"
        folder_id: The folder ID to list (default: "root" for My Drive)
        max_results: Maximum number of files to return (default 50)
    """
    service = _get_service(account)
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=max_results,
        fields="files(id, name, mimeType, createdTime, modifiedTime, size)"
    ).execute()
    files = results.get("files", [])
    return json.dumps({"account": account, "folder_id": folder_id, "files": files, "total": len(files)}, indent=2)


@mcp.tool()
def search_drive_files(account: str = "Personal", keyword: str = "", mime_type: str = "", folder_id: str = "", max_results: int = 20) -> str:
    """
    Search for files in Google Drive.

    Args:
        account: Account name — "Personal" or "Freelance"
        keyword: Search keyword (matches file name)
        mime_type: Filter by MIME type (e.g. "image/jpeg", "image/png", "application/vnd.google-apps.folder")
        folder_id: Limit search to a specific folder ID (optional)
        max_results: Maximum number of results (default 20)
    """
    service = _get_service(account)

    query_parts = ["trashed = false"]
    if keyword:
        query_parts.append(f"name contains '{keyword}'")
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")

    query = " and ".join(query_parts)
    results = service.files().list(
        q=query,
        pageSize=max_results,
        fields="files(id, name, mimeType, createdTime, modifiedTime, size, parents)"
    ).execute()
    files = results.get("files", [])
    return json.dumps({"account": account, "query": query, "files": files, "total": len(files)}, indent=2)


@mcp.tool()
def get_drive_image(account: str, file_id: str) -> Image:
    """
    Download an image from Google Drive and return it for visual analysis.

    Args:
        account: Account name — "Personal" or "Freelance"
        file_id: The file ID of the image to retrieve
    """
    service = _get_service(account)

    # Get file metadata
    file_meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    mime_type = file_meta.get("mimeType", "image/jpeg")
    fmt = mime_type.split("/")[-1].lower()  # e.g. "jpeg", "png"
    if fmt == "jpg":
        fmt = "jpeg"

    # Download file content
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return Image(data=buffer.getvalue(), format=fmt)


@mcp.tool()
def get_drive_folder_id(account: str = "Personal", folder_name: str = "") -> str:
    """
    Find a folder by name in Google Drive and return its ID.

    Args:
        account: Account name — "Personal" or "Freelance"
        folder_name: Name of the folder to search for
    """
    service = _get_service(account)
    query = f"mimeType = 'application/vnd.google-apps.folder' and name contains '{folder_name}' and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name, parents)"
    ).execute()
    folders = results.get("files", [])
    return json.dumps({"folders": folders, "total": len(folders)}, indent=2)


if __name__ == "__main__":
    mcp.run()

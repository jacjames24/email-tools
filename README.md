# email-tools

A CLI tool to view and manage unread Gmail messages using the Gmail API.

## What it does

- Fetches up to 50 unread emails from the past 30 days
- Separates emails into **Important/Primary** and **Other** categories
- Displays sender, subject, date, and a short preview for each
- Prompts you to mark all, only important, or none as read

## Requirements

- Python 3.x
- A Google Cloud project with the Gmail API enabled
- OAuth 2.0 client credentials (`client_secret_*.json`)

Install dependencies:

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

## Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create OAuth 2.0 credentials for a Desktop app.
2. Download the `client_secret_*.json` file.
3. Update `CREDENTIALS_PATH` and `TOKEN_PATH` in `gmail_tool.py` to point to your files.

## Usage

```bash
python gmail_tool.py
```

On first run, a browser window will open for Google OAuth authorization. A `token.json` file is saved for subsequent runs.

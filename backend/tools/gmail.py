import os
from pathlib import Path
import base64
from email import message_from_bytes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Read-only for now.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

# Jarvis project root
BASE_DIR = Path(__file__).resolve().parents[2]

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def get_gmail_service():
    """Authenticate with Google and return a Gmail API service."""

    creds = None

    # Existing login
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    # Token expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # First login
    if not creds or not creds.valid:

        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "credentials.json not found in the Jarvis project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        # Save token so we don't have to log in every time
        TOKEN_FILE.write_text(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def get_recent_emails(limit: int = 5):
    """Return recent Gmail messages."""

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=limit
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:

        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=[
                "From",
                "To",
                "Subject",
                "Date"
            ]
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])

        header_map = {
            header["name"]: header["value"]
            for header in headers
        }

        emails.append({
            "id": message["id"],
            "from": header_map.get("From", ""),
            "to": header_map.get("To", ""),
            "subject": header_map.get("Subject", ""),
            "date": header_map.get("Date", ""),
            "snippet": msg.get("snippet", "")
        })

    return emails

def get_email(email_id: str):
    """Get the full contents of a Gmail message by ID."""

    service = get_gmail_service()

    msg = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full"
    ).execute()

    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    header_map = {
        header["name"]: header["value"]
        for header in headers
    }

    # --------------------------------------------------------
    # Extract email body
    # --------------------------------------------------------

    body = ""

    def extract_body(part):
        """Recursively extract text/plain from MIME parts."""

        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")

            if data:
                return base64.urlsafe_b64decode(
                    data
                ).decode("utf-8", errors="ignore")

        for child in part.get("parts", []):
            result = extract_body(child)

            if result:
                return result

        return ""

    body = extract_body(payload)

    return {
        "id": email_id,
        "from": header_map.get("From", ""),
        "to": header_map.get("To", ""),
        "subject": header_map.get("Subject", ""),
        "date": header_map.get("Date", ""),
        "body": body,
        "snippet": msg.get("snippet", "")
    }

def search_emails(query: str, limit: int = 10):
    """Search Gmail using Gmail's search syntax."""

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=limit
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:
        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=[
                "From",
                "To",
                "Subject",
                "Date"
            ]
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])

        header_map = {
            header["name"]: header["value"]
            for header in headers
        }

        emails.append({
            "id": message["id"],
            "from": header_map.get("From", ""),
            "to": header_map.get("To", ""),
            "subject": header_map.get("Subject", ""),
            "date": header_map.get("Date", ""),
            "snippet": msg.get("snippet", "")
        })

    return emails
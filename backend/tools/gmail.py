from pathlib import Path
import base64

from google.auth.exceptions import RefreshError
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


def _run_oauth_flow():
    """Run the interactive Google OAuth flow and persist the new token."""
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            "credentials.json not found in the Jarvis project root."
        )

    print("[GMAIL] Starting Google OAuth authorization...")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        SCOPES,
    )

    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"[GMAIL] Authentication saved to {TOKEN_FILE.name}.")
    return creds


def get_gmail_service():
    """Authenticate with Google, refreshing or re-authorizing when needed."""
    creds = None

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES,
            )
            print("[GMAIL] Loaded saved credentials.")
        except (ValueError, OSError) as exc:
            print(f"[GMAIL] Saved token could not be loaded: {exc}")

    # Google access tokens expire. A refresh token lets google-auth obtain a
    # fresh access token without asking the user to sign in again.
    if creds and creds.expired and creds.refresh_token:
        try:
            print("[GMAIL] Access token expired; refreshing...")
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            print("[GMAIL] Access token refreshed successfully.")
        except RefreshError as exc:
            # The refresh token may have been revoked/invalidated. In that
            # case, start a fresh OAuth flow instead of silently failing.
            print(f"[GMAIL] Token refresh failed: {exc}")
            creds = None

    if not creds or not creds.valid:
        creds = _run_oauth_flow()

    return build(
        "gmail",
        "v1",
        credentials=creds,
    )


def get_recent_emails(limit: int = 5):
    """Return recent Gmail messages."""
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=limit,
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for message in messages:
        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
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
            "snippet": msg.get("snippet", ""),
        })

    return emails


def get_email(email_id: str):
    """Get the full contents of a Gmail message by ID."""
    service = get_gmail_service()

    msg = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full",
    ).execute()

    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    header_map = {
        header["name"]: header["value"]
        for header in headers
    }

    def extract_body(part):
        """Recursively extract text/plain from MIME parts."""
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="ignore"
                )

        for child in part.get("parts", []):
            result = extract_body(child)
            if result:
                return result

        return ""

    return {
        "id": email_id,
        "from": header_map.get("From", ""),
        "to": header_map.get("To", ""),
        "subject": header_map.get("Subject", ""),
        "date": header_map.get("Date", ""),
        "body": extract_body(payload),
        "snippet": msg.get("snippet", ""),
    }


def search_emails(query: str, limit: int = 10):
    """Search Gmail using Gmail's search syntax."""
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=limit,
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for message in messages:
        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
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
            "snippet": msg.get("snippet", ""),
        })

    return emails

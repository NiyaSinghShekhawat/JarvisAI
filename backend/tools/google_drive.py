import os
import webbrowser
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def get_drive_service():
    """Authenticate with Google and return a read-only Drive service."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # The existing Gmail token may not include Drive scope.
    granted_scopes = set(creds.scopes or []) if creds else set()
    if not creds or not creds.valid or "https://www.googleapis.com/auth/drive.readonly" not in granted_scopes:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "credentials.json not found in the Jarvis project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


def search_drive_files(query: str, limit: int = 10):
    """Search Google Drive by file/folder name or full text."""
    service = get_drive_service()

    safe_query = query.replace("'", "\\'")
    drive_query = (
        "trashed = false and "
        f"(name contains '{safe_query}' or fullText contains '{safe_query}')"
    )

    result = service.files().list(
        q=drive_query,
        pageSize=max(1, min(limit, 100)),
        orderBy="modifiedTime desc",
        fields="files(id,name,mimeType,modifiedTime,webViewLink,size)",
    ).execute()

    files = result.get("files", [])

    return {
        "success": True,
        "query": query,
        "files": files,
    }


def open_drive_file(file_id: str):
    """Open a specific Google Drive file in the default browser."""
    service = get_drive_service()

    file = service.files().get(
        fileId=file_id,
        fields="id,name,mimeType,webViewLink",
    ).execute()

    url = file.get("webViewLink")
    if not url:
        url = f"https://drive.google.com/open?id={file_id}"

    webbrowser.open(url)

    return {
        "success": True,
        "id": file["id"],
        "name": file.get("name", ""),
        "mimeType": file.get("mimeType", ""),
        "url": url,
    }

from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.tools.browser import open_in_browser


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def _run_oauth_flow():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError("credentials.json not found in the Jarvis project root.")

    print("[DRIVE] Starting Google OAuth authorization for Drive...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"[DRIVE] Authentication saved to {TOKEN_FILE.name}.")
    return creds


def get_drive_service():
    creds = None

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            print("[DRIVE] Loaded saved Google credentials.")
        except (ValueError, OSError) as exc:
            print(f"[DRIVE] Saved token could not be loaded: {exc}")

    if creds and creds.expired and creds.refresh_token:
        try:
            print("[DRIVE] Access token expired; refreshing...")
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            print("[DRIVE] Access token refreshed successfully.")
        except RefreshError as exc:
            print(f"[DRIVE] Token refresh failed: {exc}")
            creds = None

    granted_scopes = set(creds.scopes or []) if creds else set()
    if not creds or not creds.valid or DRIVE_SCOPE not in granted_scopes:
        creds = _run_oauth_flow()

    return build("drive", "v3", credentials=creds)


def search_drive_files(query: str, limit: int = 10, open_first: bool = False):
    """Search Drive and optionally open the best matching file."""
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
        spaces="drive",
        fields="files(id,name,mimeType,modifiedTime,webViewLink,size)",
    ).execute()

    files = result.get("files", [])
    opened = False
    opened_file = None

    if open_first and files:
        opened_file = files[0]
        url = opened_file.get("webViewLink") or f"https://drive.google.com/open?id={opened_file['id']}"
        opened = open_in_browser(url)
        print(f"[DRIVE] Opening '{opened_file.get('name', 'file')}' in browser: {opened}")

    return {
        "success": True,
        "query": query,
        "files": files,
        "opened": opened,
        "opened_file": opened_file,
    }


def open_drive_file(file_id: str = "", query: str = ""):
    """Open a Drive file by ID, or search by query and open the first match."""
    service = get_drive_service()

    if not file_id:
        if not query:
            return {"success": False, "error": "Provide a file_id or search query."}

        safe_query = query.replace("'", "\\'")
        drive_query = (
            "trashed = false and "
            f"(name contains '{safe_query}' or fullText contains '{safe_query}')"
        )
        result = service.files().list(
            q=drive_query,
            pageSize=1,
            orderBy="modifiedTime desc",
            spaces="drive",
            fields="files(id,name,mimeType,webViewLink)",
        ).execute()
        files = result.get("files", [])
        if not files:
            return {"success": False, "error": f"No Drive file found for '{query}'."}
        file = files[0]
        file_id = file["id"]
    else:
        file = service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,webViewLink",
        ).execute()

    url = file.get("webViewLink") or f"https://drive.google.com/open?id={file_id}"
    opened = open_in_browser(url)
    print(f"[DRIVE] Opening '{file.get('name', 'file')}' in browser: {opened}")

    return {
        "success": True,
        "id": file["id"],
        "name": file.get("name", ""),
        "mimeType": file.get("mimeType", ""),
        "opened": opened,
    }

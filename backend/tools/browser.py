import os
import shutil
import subprocess
import webbrowser
from pathlib import Path


def open_in_browser(url: str, prefer_chrome: bool = True) -> bool:
    """Open a URL in Chrome when available, otherwise the default browser."""
    if not url:
        return False

    if prefer_chrome and os.name == "nt":
        chrome_candidates = [
            shutil.which("chrome"),
            shutil.which("chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]

        for candidate in chrome_candidates:
            if candidate and Path(candidate).exists():
                try:
                    subprocess.Popen(
                        [candidate, "--new-window", url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except OSError:
                    pass

    try:
        return bool(webbrowser.open_new_tab(url))
    except Exception:
        return False

from urllib.parse import quote_plus

from backend.tools.browser import open_in_browser


def youtube_search(query: str):
    """Search YouTube and open the results page."""
    url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
    opened = open_in_browser(url)
    return {
        "success": opened,
        "query": query,
        "opened": "search_results",
        "browser_opened": opened,
        "error": None if opened else "Could not open YouTube in the browser.",
    }


def youtube_play(query: str):
    """Open a YouTube video directly, without downloading media."""
    try:
        import yt_dlp
    except ImportError:
        return {
            "success": False,
            "query": query,
            "error": "yt-dlp is not installed.",
        }

    # Keep the resolver fast and non-interactive. If YouTube blocks the
    # extractor, fall back to the YouTube search page rather than hanging
    # Jarvis or returning an empty response.
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 8,
        "retries": 1,
        "extractor_retries": 1,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.extract_info(f"ytsearch1:{query}", download=False)
    except Exception as exc:
        print(f"[YOUTUBE] Direct video lookup failed: {exc}")
        search_url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
        opened = open_in_browser(search_url)
        return {
            "success": opened,
            "query": query,
            "title": None,
            "opened": "search_results" if opened else None,
            "browser_opened": opened,
            "fallback": True,
            "error": None if opened else "Could not open YouTube search results.",
        }

    entries = result.get("entries") or []
    if not entries:
        search_url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
        opened = open_in_browser(search_url)
        return {
            "success": opened,
            "query": query,
            "title": None,
            "opened": "search_results" if opened else None,
            "browser_opened": opened,
            "fallback": True,
            "error": None if opened else "No YouTube result was found.",
        }

    video = entries[0]
    video_id = video.get("id")
    video_url = video.get("webpage_url")
    if not video_url and video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    if not video_url:
        return {
            "success": False,
            "query": query,
            "error": "YouTube returned a result without a video ID.",
        }

    opened = open_in_browser(video_url)
    title = video.get("title", query)
    print(f"[YOUTUBE] Opening '{title}' in browser: {opened}")
    return {
        "success": opened,
        "query": query,
        "title": title,
        "opened": "video" if opened else None,
        "browser_opened": opened,
        "error": None if opened else "Could not open the YouTube video in the browser.",
    }

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
    """Find the first YouTube result and open the actual video directly."""
    try:
        import yt_dlp
    except ImportError as exc:
        return {
            "success": False,
            "query": query,
            "error": "yt-dlp is required for direct YouTube playback. Run: pip install yt-dlp",
        }

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.extract_info(f"ytsearch1:{query}", download=False)
    except Exception as exc:
        print(f"[YOUTUBE] Search failed: {exc}")
        return {
            "success": False,
            "query": query,
            "error": f"Could not resolve a YouTube video: {exc}",
        }

    entries = result.get("entries") or []
    if not entries:
        return {"success": False, "query": query, "error": "No YouTube video found."}

    video = entries[0]
    video_id = video.get("id")
    video_url = video.get("webpage_url")
    if not video_url and video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    if not video_url:
        return {
            "success": False,
            "query": query,
            "error": "YouTube returned a result without a playable URL.",
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

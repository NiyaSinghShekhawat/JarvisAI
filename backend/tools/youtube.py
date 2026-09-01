from urllib.parse import quote_plus

import webbrowser

from backend.tools.browser import open_in_browser


def youtube_search(query: str):
    """Search YouTube and open the results page."""
    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    opened = open_in_browser(url)

    return {
        "success": True,
        "query": query,
        "opened": "search_results",
        "browser_opened": opened,
    }


def youtube_play(query: str):
    """Find the first YouTube result and open the actual video directly."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is required for direct YouTube playback. Run: pip install yt-dlp"
        ) from exc

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            f"ytsearch1:{query}",
            download=False,
        )

    entries = result.get("entries") or []
    if not entries:
        return {
            "success": False,
            "query": query,
            "error": "No YouTube video found.",
        }

    video = entries[0]
    video_url = video.get("webpage_url")

    if not video_url:
        video_id = video.get("id")
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

    if not video_url:
        return {
            "success": False,
            "query": query,
            "error": "YouTube returned a result without a playable URL.",
        }

    opened = open_in_browser(video_url)

    print(
        f"[YOUTUBE] Opening '{video.get('title', query)}' in browser: {opened}"
    )

    return {
        "success": True,
        "query": query,
        "title": video.get("title", ""),
        "opened": "video",
        "browser_opened": opened,
    }

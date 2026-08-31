import webbrowser
from urllib.parse import quote_plus


def youtube_search(query: str):
    """Search YouTube and open the results page."""
    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    webbrowser.open(url)

    return {
        "success": True,
        "query": query,
        "url": url,
        "opened": "search_results",
    }


def youtube_play(query: str):
    """Find the first YouTube result and open the actual video."""
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
    video_url = video.get("webpage_url") or video.get("url")

    if not video_url:
        return {
            "success": False,
            "query": query,
            "error": "YouTube returned a result without a playable URL.",
        }

    webbrowser.open(video_url)

    return {
        "success": True,
        "query": query,
        "title": video.get("title", ""),
        "url": video_url,
        "opened": "video",
    }

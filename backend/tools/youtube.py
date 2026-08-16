import webbrowser
from urllib.parse import quote_plus


def youtube_search(query: str):

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    webbrowser.open(url)

    return {
        "success": True,
        "query": query,
        "url": url
    }
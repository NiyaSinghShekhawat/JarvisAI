from .web_search import web_search


def research(query: str, max_results: int = 8):
    """
    Perform a research-oriented web search.

    Returns:
        A cleaned list of sources containing
        title, URL and snippet.
    """

    results = web_search(
        query,
        max_results=max_results
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    seen_urls = set()
    cleaned_results = []

    for result in results:

        url = result.get("url")

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        cleaned_results.append({
            "title": result.get("title", ""),
            "url": url,
            "snippet": result.get("snippet", "")
        })

    # --------------------------------------------------------
    # LIMIT RESULTS
    # --------------------------------------------------------

    return cleaned_results[:max_results]
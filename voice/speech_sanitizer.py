import re


_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)", re.IGNORECASE)
_MARKDOWN_PATTERN = re.compile(r"[*_`~]+")


def speech_safe_text(text: str) -> str:
    """Convert an LLM response into natural text suitable for TTS."""
    if not text:
        return ""

    # Keep the readable label from [Open this](https://...).
    text = _MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    # Never speak raw URLs.
    text = _URL_PATTERN.sub("", text)
    # Markdown is useful visually, but not when spoken.
    text = _MARKDOWN_PATTERN.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()

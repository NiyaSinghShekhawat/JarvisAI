from backend.tools.time_tool import get_time
from backend.tools.weather_tool import get_weather
from backend.tools.web_search import web_search
from backend.tools.research import research
from backend.tools.youtube import youtube_search, youtube_play
from backend.tools.gmail import (
    get_recent_emails,
    get_email,
    search_emails,
)
from backend.tools.google_drive import (
    search_drive_files,
    open_drive_file,
)


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = {
    "get_time": get_time,
    "get_weather": get_weather,
    "web_search": web_search,
    "research": research,
    "youtube_search": youtube_search,
    "youtube_play": youtube_play,
    "get_recent_emails": get_recent_emails,
    "get_email": get_email,
    "search_emails": search_emails,
    "search_drive_files": search_drive_files,
    "open_drive_file": open_drive_file,
}


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get the current weather for a city or location. "
                "Use this whenever the user asks about weather, temperature, "
                "rain, humidity, wind, or conditions."
            ),
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_name": {"type": "string"}
                },
                "required": ["timezone_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts, websites, and up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research",
            "description": "Research a topic using multiple web sources.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search YouTube and open the results page.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_play",
            "description": "Find the first relevant YouTube video for a request and open the actual video directly. Use this when the user says play, watch, start, or open a specific video/song/tutorial on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Read the user's recent Gmail emails. Use this when the user asks to check, read, show, summarize, or review emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 5}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_email",
            "description": "Read the full contents of a specific Gmail email.",
            "parameters": {
                "type": "object",
                "properties": {"email_id": {"type": "string"}},
                "required": ["email_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search Gmail messages by sender, subject, keywords, date, or Gmail search criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_drive_files",
            "description": "Search the user's Google Drive for files or folders by name or content. Use when the user asks to find, locate, or look for a Drive file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_drive_file",
            "description": "Open a specific Google Drive file in the user's browser using its Drive file ID.",
            "parameters": {
                "type": "object",
                "properties": {"file_id": {"type": "string"}},
                "required": ["file_id"],
            },
        },
    },
]


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool(tool_name, arguments):
    if tool_name not in TOOLS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    try:
        return TOOLS[tool_name](**arguments)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

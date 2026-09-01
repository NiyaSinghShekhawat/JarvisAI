from backend.tools.time_tool import get_time
from backend.tools.weather_tool import get_weather
from backend.tools.web_search import web_search
from backend.tools.research import research
from backend.tools.youtube import youtube_search, youtube_play
from backend.tools.gmail import get_recent_emails, get_email, search_emails
from backend.tools.google_drive import search_drive_files, open_drive_file


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


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city or location.",
            "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time for a location.",
            "parameters": {"type": "object", "properties": {"timezone_name": {"type": "string"}}, "required": ["timezone_name"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts, websites, and up-to-date information.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research",
            "description": "Research a topic using multiple web sources.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search YouTube and open the results page. Use this when the user wants search results rather than a specific video.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_play",
            "description": "Find the first relevant YouTube video and OPEN THE ACTUAL VIDEO in Chrome. Use this when the user says play, watch, start, or open a specific video/song/tutorial. Do not use web_search after this just to provide a link; the browser tool already opens it.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Read the user's recent Gmail emails.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 5}}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_email",
            "description": "Read the full contents of a specific Gmail email.",
            "parameters": {"type": "object", "properties": {"email_id": {"type": "string"}}, "required": ["email_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search Gmail messages by sender, subject, keywords, date, or Gmail search criteria.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_drive_files",
            "description": "Search Google Drive. If the user asks to find/search AND open the file, set open_first=true so Jarvis opens the best match in Chrome immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "open_first": {"type": "boolean", "default": False},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_drive_file",
            "description": "Open a Google Drive file in Chrome. Use file_id when known; otherwise use query to find the requested file and open the best match. This performs the browser action itself, so do not merely return a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": [],
            },
        },
    },
]


def execute_tool(tool_name, arguments):
    if tool_name not in TOOLS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    try:
        return TOOLS[tool_name](**arguments)
    except Exception as e:
        return {"success": False, "error": str(e)}

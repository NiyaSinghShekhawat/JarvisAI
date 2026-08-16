from backend.tools.time_tool import get_time
from backend.tools.weather_tool import get_weather
from backend.tools.web_search import web_search
from backend.tools.research import research
from backend.tools.youtube import youtube_search
from backend.tools.gmail import (
    get_recent_emails,
    get_email,
    search_emails
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
    "get_recent_emails": get_recent_emails,
    "get_email": get_email,
    "search_emails": search_emails,
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
                "Use this when the user asks about weather, temperature, "
                "rain, humidity, wind, or conditions. "
                "For a general weather question, the final response should "
                "normally mention only the temperature and simple weather "
                "condition. Only mention humidity, wind, precipitation, etc. "
                "when the user specifically asks for them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location."
                    }
                },
                "required": ["location"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": (
                "Get the current time for a location. "
                "Use this when the user asks what time it is. "
                "Return the exact current local time. "
                "The final response should normally contain only the time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_name": {
                        "type": "string",
                        "description": (
                            "IANA timezone such as "
                            "Asia/Kolkata, Asia/Tokyo, "
                            "Europe/London, or America/New_York."
                        ),
                    }
                },
                "required": ["timezone_name"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information, "
                "news, facts, websites, and up-to-date information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query."
                    }
                },
                "required": ["query"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "research",
            "description": (
                "Research a topic using multiple web sources. "
                "Use for academic research or detailed investigation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Research topic or question."
                    }
                },
                "required": ["query"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": (
                "Search YouTube for videos, songs, tutorials, "
                "channels, movies, or other content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for on YouTube."
                    }
                },
                "required": ["query"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": (
                "Read the user's recent Gmail emails. "
                "Use this when the user asks to check, read, "
                "show, summarize, or review emails."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails.",
                        "default": 5
                    }
                },
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_email",
            "description": (
                "Read the full contents of a specific Gmail email."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail message ID."
                    }
                },
                "required": ["email_id"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": (
                "Search Gmail messages by sender, subject, "
                "keywords, date, or other Gmail search criteria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Gmail query such as "
                            "from:professor@gmail.com, "
                            "subject:DBMS, is:unread, or exam."
                        )
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum emails to return.",
                        "default": 10
                    }
                },
                "required": ["query"],
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
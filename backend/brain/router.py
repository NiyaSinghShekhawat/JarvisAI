import json
import time
from typing import Generator

# from backend.brain.llm import (
#     get_llm,
#     stream_response,
#     groq_manager,
#     get_provider_info,
#     SYSTEM_PROMPT
# )

from backend.brain.llm import (
    get_llm,
    get_provider_info,
    SYSTEM_PROMPT
)

from backend.tools.tools_registry import (
    TOOLS,
    TOOL_DEFINITIONS,
    execute_tool
)

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
from backend.tools.tools_registry import TOOL_DEFINITIONS, execute_tool
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
    "search_emails": search_emails
}


# ============================================================
# CONFIGURATION
# ============================================================

MAX_TOOL_ROUNDS = 5


# ============================================================
# HELPERS
# ============================================================

def _build_messages(message: str, conversation=None):
    """
    Build the conversation sent to the LLM.

    conversation is expected to contain previous messages
    in OpenAI-compatible format.
    """

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if conversation:
        messages.extend(conversation)

    messages.append({
        "role": "user",
        "content": message
    })

    return messages


def _clean_tool_arguments(arguments):
    """
    Groq sometimes returns arguments as a JSON string.
    Normalize them into a Python dictionary.
    """

    if arguments is None:
        return {}

    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {}

    return {}


# ============================================================
# PROVIDER INFO
# ============================================================

def get_router_status():
    """
    Used by the UI if we want to display the current provider.
    """

    return get_provider_info()


# ============================================================
# NORMAL REQUEST
# ============================================================

def process_request(
    user_input: str,
    conversation=None
):
    """
    Process one complete Jarvis request.

    Supports:
        - normal LLM responses
        - tool calling
        - conversation memory
        - Groq key rotation through llm.py
    """

    messages = _build_messages(
        user_input,
        conversation
    )

    for _ in range(MAX_TOOL_ROUNDS):

        client, model = get_llm()

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=128,
        )

        assistant_message = response.choices[0].message

        # ----------------------------------------------------
        # NO TOOL CALL
        # ----------------------------------------------------

        if not assistant_message.tool_calls:

            content = assistant_message.content or ""

            if conversation is not None:
                conversation.append({
                    "role": "user",
                    "content": user_input
                })

                conversation.append({
                    "role": "assistant",
                    "content": content
                })

            return {
                "type": "text",
                "content": content
            }

        # ----------------------------------------------------
        # TOOL CALLS
        # ----------------------------------------------------

        messages.append({
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    }
                }
                for call in assistant_message.tool_calls
            ]
        })

        for call in assistant_message.tool_calls:

            tool_name = call.function.name

            arguments = _clean_tool_arguments(
                call.function.arguments
            )

            print(
                f"[Tool] {tool_name}({arguments})"
            )

            try:

                result = execute_tool(
                    tool_name,
                    arguments
                )

            except Exception as e:

                result = {
                    "error": str(e)
                }

            # ----------------------------------------------
            # Feed tool result back to LLM
            # ----------------------------------------------

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str
                )
            })

    return {
        "type": "text",
        "content": (
            "I couldn't complete that request."
        )
    }


# ============================================================
# STREAMING REQUEST
# ============================================================

def process_request_stream(
    user_input: str,
    conversation=None
) -> Generator[dict, None, None]:

    messages = _build_messages(
        user_input,
        conversation
    )

    for _ in range(MAX_TOOL_ROUNDS):

        client, model = get_llm()

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=128,
            stream=True,
        )

        full_response = ""
        tool_calls = {}

        # ----------------------------------------------------
        # STREAM TOKENS
        # ----------------------------------------------------

        for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Normal text
            if delta.content:

                full_response += delta.content

                yield {
                    "type": "text",
                    "content": delta.content
                }

            # Tool calls
            if delta.tool_calls:

                for tool_call in delta.tool_calls:

                    index = tool_call.index

                    if index not in tool_calls:
                        tool_calls[index] = {
                            "id": "",
                            "name": "",
                            "arguments": ""
                        }

                    if tool_call.id:
                        tool_calls[index]["id"] = tool_call.id

                    if tool_call.function:

                        if tool_call.function.name:
                            tool_calls[index]["name"] += (
                                tool_call.function.name
                            )

                        if tool_call.function.arguments:
                            tool_calls[index]["arguments"] += (
                                tool_call.function.arguments
                            )

        # ----------------------------------------------------
        # NORMAL RESPONSE COMPLETE
        # ----------------------------------------------------

        if not tool_calls:

            if conversation is not None:

                conversation.append({
                    "role": "user",
                    "content": user_input
                })

                conversation.append({
                    "role": "assistant",
                    "content": full_response
                })

            yield {
                "type": "done"
            }

            return

        # ----------------------------------------------------
        # TOOL EXECUTION
        # ----------------------------------------------------

        assistant_tool_calls = []

        for call in tool_calls.values():

            arguments = _clean_tool_arguments(
                call["arguments"]
            )

            assistant_tool_calls.append({
                "id": call["id"],
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["arguments"],
                }
            })

        messages.append({
            "role": "assistant",
            "content": full_response or None,
            "tool_calls": assistant_tool_calls
        })

        for call in tool_calls.values():

            tool_name = call["name"]

            arguments = _clean_tool_arguments(
                call["arguments"]
            )

            print(
                f"[Tool] {tool_name}({arguments})"
            )

            yield {
                "type": "tool",
                "tool": tool_name,
                "arguments": arguments
            }

            try:

                result = execute_tool(
                    tool_name,
                    arguments
                )

            except Exception as e:

                result = {
                    "error": str(e)
                }

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str
                )
            })

    yield {
        "type": "error",
        "content": "I couldn't complete that request."
    }

# def process_request_stream(user_message, conversation):

#     tool_sources = []

#     # --------------------------------------------------------
#     # ADD USER MESSAGE
#     # --------------------------------------------------------

#     conversation.append({
#         "role": "user",
#         "content": user_message,
#     })

#     # --------------------------------------------------------
#     # FIRST LLM CALL
#     # --------------------------------------------------------

#     streamed_text = ""

#     tool_call_result = None

#     for event in stream_response(
#         conversation,
#         tools=TOOL_DEFINITIONS
#     ):

#         # ---------------------------------------------
#         # TEXT TOKEN
#         # ---------------------------------------------

#         if event["type"] == "text":

#             token = event["content"]

#             streamed_text += token

#             yield {
#                 "type": "text",
#                 "content": token,
#             }

#         # ---------------------------------------------
#         # TOOL CALL
#         # ---------------------------------------------

#         elif event["type"] == "tool_call":

#             tool_call_result = event["tool_calls"]

#     # --------------------------------------------------------
#     # NORMAL RESPONSE
#     # --------------------------------------------------------

#     if not tool_call_result:

#         conversation.append({
#             "role": "assistant",
#             "content": streamed_text,
#         })

#         yield {
#             "type": "done",
#             "response": streamed_text,
#             "sources": tool_sources,
#         }

#         return

#     # --------------------------------------------------------
#     # SAVE TOOL CALL MESSAGE
#     # --------------------------------------------------------

#     assistant_dict = {
#         "role": "assistant",
#         "content": streamed_text,
#         "tool_calls": tool_call_result,
#     }

#     conversation.append(assistant_dict)

#     # --------------------------------------------------------
#     # EXECUTE TOOLS
#     # --------------------------------------------------------

#     for tool_call in tool_call_result:

#         tool_name = tool_call["function"]["name"]

#         try:
#             arguments = json.loads(
#                 tool_call["function"]["arguments"]
#             )

#         except json.JSONDecodeError:

#             result = {
#                 "success": False,
#                 "error": "Invalid tool arguments generated by the model."
#             }

#         else:

#             print(
#                 f"[Tool] {tool_name}({arguments})"
#             )

#             yield {
#                 "type": "tool",
#                 "name": tool_name,
#                 "arguments": arguments,
#             }

#             result = execute_tool(
#                 tool_name,
#                 arguments
#             )

#         # ----------------------------------------------------
#         # COLLECT SOURCES
#         # ----------------------------------------------------

#         if tool_name in ["web_search", "research"]:

#             if isinstance(result, list):
#                 tool_sources.extend(result)

#         # ----------------------------------------------------
#         # GIVE RESULT BACK TO MODEL
#         # ----------------------------------------------------

#         conversation.append({
#             "role": "tool",
#             "tool_call_id": tool_call["id"],
#             "content": serialize_tool_result(result),
#         })

#     # --------------------------------------------------------
#     # SECOND LLM CALL
#     # --------------------------------------------------------

#     final_text = ""

#     for event in stream_response(conversation):

#         if event["type"] == "text":

#             token = event["content"]

#             final_text += token

#             yield {
#                 "type": "text",
#                 "content": token,
#             }

#     # --------------------------------------------------------
#     # SAVE FINAL RESPONSE
#     # --------------------------------------------------------

#     conversation.append({
#         "role": "assistant",
#         "content": final_text,
#     })

#     yield {
#         "type": "done",
#         "response": final_text,
#         "sources": tool_sources,
#     }
# # ============================================================
# # TOOL DEFINITIONS
# # ============================================================

# TOOL_DEFINITIONS = [

#     # --------------------------------------------------------
#     # WEATHER
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "get_weather",
#             "description": (
#                 "Get the current weather for a city or location. "
#                 "Use this whenever the user asks about weather, "
#                 "temperature, rain, humidity, wind, or conditions."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "location": {
#                         "type": "string",
#                         "description": (
#                             "The city or location, for example "
#                             "Hyderabad, Tokyo, London, or New York."
#                         ),
#                     }
#                 },
#                 "required": ["location"],
#             },
#         },
#     },

#     # --------------------------------------------------------
#     # TIME
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "get_time",
#             "description": (
#                 "Get the current time for a location. "
#                 "Use this when the user asks what time it is."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "timezone_name": {
#                         "type": "string",
#                         "description": (
#                             "IANA timezone name such as "
#                             "Asia/Kolkata, Asia/Tokyo, "
#                             "Europe/London, or America/New_York."
#                         ),
#                     }
#                 },
#                 "required": ["timezone_name"],
#             },
#         },
#     },

#     # --------------------------------------------------------
#     # WEB SEARCH
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "web_search",
#             "description": (
#                 "Search the web for current information, "
#                 "research, news, facts, websites, papers, "
#                 "and other information that may require "
#                 "up-to-date sources."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The search query.",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#     },

#     # --------------------------------------------------------
#     # RESEARCH
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "research",
#             "description": (
#                 "Research a topic using multiple web sources. "
#                 "Use this when the user asks for research, "
#                 "thesis information, academic information, "
#                 "reliable sources, recent developments, "
#                 "or a detailed factual investigation."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": (
#                             "The topic or research question "
#                             "to investigate."
#                         ),
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#     },

#     # --------------------------------------------------------
#     # YOUTUBE
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "youtube_search",
#             "description": (
#                 "Open YouTube and search for a video, song, "
#                 "channel, topic, tutorial, movie, or other content."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "What to search for on YouTube.",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#     },

#     # --------------------------------------------------------
#     # GMAIL
#     # --------------------------------------------------------

#     {
#         "type": "function",
#         "function": {
#             "name": "get_recent_emails",
#             "description": (
#                 "Read the user's recent Gmail emails. "
#                 "Use this when the user asks to check, read, "
#                 "show, summarize, or review their emails. "
#                 "The Gmail tool provides the actual email data. "
#                 "Never claim that Gmail is inaccessible if this "
#                 "tool has returned email data."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "limit": {
#                         "type": "integer",
#                         "description": (
#                             "Maximum number of emails to retrieve."
#                         ),
#                         "default": 5,
#                     }
#                 },
#                 "required": [],
#             },
#         },
#     },

#     {
#         "type": "function",
#         "function": {
#             "name": "get_email",
#             "description": (
#                 "Read the full contents of a specific Gmail email "
#                 "using its email ID. Use this when the user wants "
#                 "to read or open a specific email."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "email_id": {
#                         "type": "string",
#                         "description": "The Gmail message ID."
#                     }
#                 },
#                 "required": ["email_id"]
#             }
#         }
#     },

#     {
#         "type": "function",
#         "function": {
#             "name": "search_emails",
#             "description": (
#                 "Search the user's Gmail messages. "
#                 "Use this when the user asks to find emails "
#                 "by sender, subject, keywords, date, or other criteria."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": (
#                             "Gmail search query, such as "
#                             "from:professor@gmail.com, "
#                             "subject:DBMS, "
#                             "after:2026/08/10, "
#                             "is:unread, or exam"
#                         )
#                     },
#                     "limit": {
#                         "type": "integer",
#                         "description": "Maximum number of emails to return.",
#                         "default": 10
#                     }
#                 },
#                 "required": ["query"]
#             }
#         }
#     }
# ]


# # ============================================================
# # TOOL EXECUTION
# # ============================================================

# def execute_tool(tool_name, arguments):

#     if tool_name not in TOOLS:
#         return {
#             "success": False,
#             "error": f"Unknown tool: {tool_name}",
#         }

#     try:
#         tool = TOOLS[tool_name]

#         result = tool(**arguments)

#         return result

#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e),
#         }


# # ============================================================
# # SERIALIZE TOOL RESULT
# # ============================================================

# def serialize_tool_result(result):
#     """
#     Convert any tool result into something safely
#     serializable by the OpenAI/Groq API.
#     """

#     try:
#         return json.dumps(
#             result,
#             ensure_ascii=False,
#             default=str
#         )

#     except Exception:
#         return json.dumps({
#             "success": False,
#             "error": "Tool returned data that could not be serialized."
#         })


# # ============================================================
# # PROCESS REQUEST
# # ============================================================

# def process_request(user_message, conversation):

#     tool_sources = []

#     # --------------------------------------------------------
#     # ADD USER MESSAGE
#     # --------------------------------------------------------

#     conversation.append({
#         "role": "user",
#         "content": user_message,
#     })

#     # --------------------------------------------------------
#     # FIRST LLM CALL
#     #
#     # Purpose:
#     # Decide whether a tool is required.
#     # --------------------------------------------------------
    
#     provider = get_llm()
#     client = provider["client"]
#     model = provider["model"]
#     response = groq_manager.execute(
#         lambda client: client.chat.completions.create(
#             model=model,
#             messages=conversation,
#             tools=TOOL_DEFINITIONS,
#             tool_choice="auto",
#             temperature=0.2,
#             max_tokens=128,
#         )
#     )

#     assistant_message = response.choices[0].message

#     # --------------------------------------------------------
#     # NORMAL RESPONSE
#     #
#     # No tool required.
#     # --------------------------------------------------------

#     if not assistant_message.tool_calls:

#         content = assistant_message.content or ""

#         conversation.append({
#             "role": "assistant",
#             "content": content,
#         })

#         return {
#             "response": content,
#             "sources": tool_sources,
#         }

#     # --------------------------------------------------------
#     # SAVE ASSISTANT TOOL-CALL MESSAGE
#     # --------------------------------------------------------

#     assistant_dict = {
#         "role": "assistant",
#         "content": assistant_message.content or "",
#         "tool_calls": [],
#     }

#     for tool_call in assistant_message.tool_calls:

#         assistant_dict["tool_calls"].append({
#             "id": tool_call.id,
#             "type": "function",
#             "function": {
#                 "name": tool_call.function.name,
#                 "arguments": tool_call.function.arguments,
#             },
#         })

#     conversation.append(assistant_dict)

#     # --------------------------------------------------------
#     # EXECUTE ALL TOOL CALLS
#     # --------------------------------------------------------

#     for tool_call in assistant_message.tool_calls:

#         tool_name = tool_call.function.name

#         # ----------------------------------------------------
#         # PARSE ARGUMENTS
#         # ----------------------------------------------------

#         try:

#             arguments = json.loads(
#                 tool_call.function.arguments
#             )

#         except (json.JSONDecodeError, TypeError):

#             error_result = {
#                 "success": False,
#                 "error": "Invalid tool arguments generated by the model.",
#             }

#             conversation.append({
#                 "role": "tool",
#                 "tool_call_id": tool_call.id,
#                 "content": serialize_tool_result(error_result),
#             })

#             continue

#         # ----------------------------------------------------
#         # SHOW TOOL EXECUTION
#         # ----------------------------------------------------

#         print(
#             f"[Tool] {tool_name}({arguments})"
#         )

#         # ----------------------------------------------------
#         # EXECUTE TOOL
#         # ----------------------------------------------------

#         result = execute_tool(
#             tool_name,
#             arguments
#         )

#         # ----------------------------------------------------
#         # COLLECT SOURCES
#         # ----------------------------------------------------

#         if tool_name in ["web_search", "research"]:

#             if isinstance(result, list):
#                 tool_sources.extend(result)

#         # ----------------------------------------------------
#         # IMPORTANT:
#         #
#         # Give the actual tool result back to the LLM.
#         # ----------------------------------------------------

#         serialized_result = serialize_tool_result(result)

#         conversation.append({
#             "role": "tool",
#             "tool_call_id": tool_call.id,
#             "content": serialized_result,
#         })

#     # --------------------------------------------------------
#     # SECOND LLM CALL
#     #
#     # Purpose:
#     # Turn the actual tool result into a natural response.
#     # --------------------------------------------------------

#     final_instruction = {
#         "role": "system",
#         "content": (
#             "IMPORTANT: One or more tools were just executed. "
#             "Use the tool results above as the source of truth. "
#             "Answer the user's original request using those results. "
#             "Do not claim that you lack access to a service when "
#             "the corresponding tool successfully returned data. "
#             "Do not mention internal tools, tool calls, APIs, "
#             "or implementation details unless the user asks."
#         ),
#     }

#     # We don't permanently store this instruction in memory.
#     final_messages = conversation + [final_instruction]

#     provider = get_llm()
#     client = provider["client"]
#     model = provider["model"]
#     final_response = client.chat.completions.create(
#         model=model,
#         messages=final_messages,
#         temperature=0.2,
#         max_tokens=256,
#     )

#     final_content = (
#         final_response.choices[0].message.content
#         or "I couldn't generate a response from the tool result."
#     )

#     # --------------------------------------------------------
#     # SAVE FINAL RESPONSE
#     # --------------------------------------------------------

#     conversation.append({
#         "role": "assistant",
#         "content": final_content,
#     })

#     return {
#         "response": final_content,
#         "sources": tool_sources,
#     }
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()


# ============================================================
# LOCAL LM STUDIO
# ============================================================

LOCAL_BASE_URL = "http://localhost:1234/v1"
LOCAL_API_KEY = "lm-studio"
LOCAL_MODEL = "qwen/qwen3-1.7b"


# ============================================================
# GROQ
# ============================================================

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"


# ============================================================
# GROQ KEY MANAGER
# ============================================================

class GroqManager:

    def __init__(self):

        self.keys = [
            os.getenv("GROQ_API_KEY_1"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
            os.getenv("GROQ_API_KEY_4"),
            os.getenv("GROQ_API_KEY_5"),
        ]

        self.keys = [
            key for key in self.keys
            if key
        ]

        self.current_index = 0

    # --------------------------------------------------------
    # CURRENT KEY
    # --------------------------------------------------------

    @property
    def current_key(self):

        if not self.keys:
            return None

        return self.keys[self.current_index]

    # --------------------------------------------------------
    # CLIENT
    # --------------------------------------------------------

    def get_client(self):

        if not self.keys:

            raise RuntimeError(
                "No Groq API keys configured. "
                "Add GROQ_API_KEY_1, GROQ_API_KEY_2, etc. "
                "to your .env file."
            )

        return OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=self.current_key
        )

    # --------------------------------------------------------
    # ROTATE
    # --------------------------------------------------------

    def rotate(self):

        if len(self.keys) <= 1:
            return False

        old_index = self.current_index

        self.current_index = (
            self.current_index + 1
        ) % len(self.keys)

        print(
            f"[LLM] Groq key rotated: "
            f"{old_index + 1} -> "
            f"{self.current_index + 1}"
        )

        return True

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def info(self):

        return {
            "provider": "groq",
            "model": GROQ_MODEL,
            "total_keys": len(self.keys),
            "current_key": (
                self.current_index + 1
                if self.keys
                else None
            )
        }


groq_manager = GroqManager()


# ============================================================
# LOCAL CLIENT
# ============================================================

local_client = OpenAI(
    base_url=LOCAL_BASE_URL,
    api_key=LOCAL_API_KEY
)


# ============================================================
# GET LLM
# ============================================================

def get_llm(provider=None):

    provider = (
        provider or LLM_PROVIDER
    ).lower()

    if provider == "groq":

        return (
            groq_manager.get_client(),
            GROQ_MODEL
        )

    if provider == "local":

        return (
            local_client,
            LOCAL_MODEL
        )

    raise ValueError(
        f"Unknown LLM provider: {provider}"
    )


# ============================================================
# PROVIDER INFORMATION
# ============================================================

def get_provider_info():

    if LLM_PROVIDER == "groq":

        return groq_manager.info()

    return {
        "provider": "local",
        "model": LOCAL_MODEL,
        "total_keys": 0,
        "current_key": None
    }


# ============================================================
# DEFAULT MODEL
# ============================================================

MODEL = (
    GROQ_MODEL
    if LLM_PROVIDER == "groq"
    else LOCAL_MODEL
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Jarvis, a personal AI assistant.

Be concise, practical, conversational and natural.

Speak like an intelligent personal assistant, not like an API,
database, report, or technical documentation.

Rules:

- For greetings, respond naturally and briefly.
- For simple factual questions, answer briefly.
- Do not give long explanations unless the user asks.
- Do not repeat the user's question.
- Do not explain your reasoning.
- Avoid unnecessary lists.
- Avoid unnecessary technical details.
- Never dump raw tool output to the user.
- Convert tool results into a natural conversational response.

TIME:

- When the user asks for the current time, give only the time.
- Do not explain timezone details unless asked.
- Do not mention seconds.
- Example:
  "It's 11:20 AM."

WEATHER:

- When the user asks for general/current weather, give only:
  - temperature
  - simple condition such as sunny, cloudy, rainy, light drizzle, etc.
- Do NOT automatically mention humidity.
- Do NOT automatically mention wind speed.
- Do NOT automatically mention precipitation probability.
- Do NOT list multiple weather metrics.
- Example:
  "It's 28°C in Hyderabad with light drizzle."
- If the user specifically asks about humidity, wind, rain probability,
  or another weather metric, then provide that metric.

VOICE:

- Responses intended to be spoken should sound natural.
- Prefer short conversational sentences.
- Do not sound robotic or overly formal.
- Do not say things like "The current weather conditions indicate..."
- Say things like "It's 28°C in Hyderabad with light drizzle."
- Do not unnecessarily say "Certainly", "Of course", or "As an AI assistant".

When using research or web search results, rely only on
the information provided by the tools.

Never invent sources, URLs, papers, authors or citations.

When the user asks for sources, include the actual sources
returned by the research tool.

Prefer authoritative and academic sources when available.

Tools:

- You can use tools to access Gmail, weather, web search,
  research, YouTube and other available services.
- When the user asks about emails, use the Gmail tool.
- Never claim to have accessed an email unless the Gmail
  tool actually returned it.
"""


# ============================================================
# RATE LIMIT DETECTION
# ============================================================

def _is_rate_limit_error(error):

    status = getattr(error, "status_code", None)

    if status == 429:
        return True

    message = str(error).lower()

    return (
        "rate limit" in message
        or "rate_limit" in message
        or "too many requests" in message
        or "quota" in message
    )


# ============================================================
# NORMAL REQUEST
# ============================================================

# ============================================================
# NORMAL REQUEST WITH GROQ KEY ROTATION
# ============================================================

def ask_jarvis(message: str, messages=None, provider=None):

    if messages is None:

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    messages.append({
        "role": "user",
        "content": message
    })

    provider = (
        provider or LLM_PROVIDER
    ).lower()

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    if provider == "local":

        client, model = get_llm("local")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=128
        )

        return response.choices[0].message.content

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    if provider != "groq":
        raise ValueError(
            f"Unknown LLM provider: {provider}"
        )

    attempts = len(groq_manager.keys)

    if attempts == 0:
        raise RuntimeError(
            "No Groq API keys configured."
        )

    for attempt in range(attempts):

        try:

            client, model = get_llm("groq")

            print(
                f"[LLM] Using Groq key "
                f"{groq_manager.current_index + 1}/{attempts}"
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=128
            )

            return response.choices[0].message.content

        except Exception as e:

            error_text = str(e).lower()

            is_rate_limit = (
                "rate limit" in error_text
                or "429" in error_text
                or "too many requests" in error_text
                or "quota" in error_text
            )

            if not is_rate_limit:
                raise

            print(
                f"[LLM] Groq key "
                f"{groq_manager.current_index + 1} "
                f"hit rate limit."
            )

            if attempt < attempts - 1:

                groq_manager.rotate()

            else:

                raise RuntimeError(
                    "All configured Groq API keys "
                    "have reached their limits."
                ) from e


# ============================================================
# STREAMING RESPONSE
# ============================================================
# ============================================================
# STREAMING RESPONSE WITH GROQ KEY ROTATION
# ============================================================

def stream_response(messages, provider=None):

    provider = (
        provider or LLM_PROVIDER
    ).lower()

    # --------------------------------------------------------
    # LOCAL MODEL
    # --------------------------------------------------------

    if provider == "local":

        client, model = get_llm("local")

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=128,
            stream=True
        )

        for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta.content:
                yield delta.content

        return

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    if provider != "groq":
        raise ValueError(
            f"Unknown LLM provider: {provider}"
        )

    attempts = len(groq_manager.keys)

    if attempts == 0:
        raise RuntimeError(
            "No Groq API keys configured."
        )

    for attempt in range(attempts):

        try:

            client, model = get_llm("groq")

            print(
                f"[LLM] Using Groq key "
                f"{groq_manager.current_index + 1}/{attempts}"
            )

            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=128,
                stream=True
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Rate-limit errors can happen while iterating
            # over the stream, so the try block must include
            # the loop itself.
            # ------------------------------------------------

            for chunk in stream:

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                if delta.content:
                    yield delta.content

            # Successful completion
            return

        except Exception as e:

            error_text = str(e).lower()

            # -----------------------------------------------
            # Detect Groq rate-limit errors
            # -----------------------------------------------

            is_rate_limit = (
                "rate limit" in error_text
                or "429" in error_text
                or "too many requests" in error_text
                or "quota" in error_text
            )

            if not is_rate_limit:
                raise

            print(
                f"[LLM] Groq key "
                f"{groq_manager.current_index + 1} "
                f"hit rate limit during streaming."
            )

            # -----------------------------------------------
            # Try next key
            # -----------------------------------------------

            if attempt < attempts - 1:

                groq_manager.rotate()

                print(
                    f"[LLM] Retrying with Groq key "
                    f"{groq_manager.current_index + 1}."
                )

            else:

                raise RuntimeError(
                    "All configured Groq API keys "
                    "have reached their limits."
                ) from e

    raise RuntimeError(
        "Unable to obtain a response from Groq."
    )





# import os
# from dotenv import load_dotenv
# from openai import OpenAI

# load_dotenv()

# # ============================================================
# # CONFIGURATION
# # ============================================================

# LOCAL_BASE_URL = "http://localhost:1234/v1"
# LOCAL_API_KEY = "lm-studio"
# LOCAL_MODEL = "qwen/qwen3-1.7b"

# GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# GROQ_MODEL = "llama-3.3-70b-versatile"


# # ============================================================
# # CLIENTS
# # ============================================================

# local_client = OpenAI(
#     base_url=LOCAL_BASE_URL,
#     api_key=LOCAL_API_KEY
# )

# groq_client = None

# if GROQ_API_KEY:
#     groq_client = OpenAI(
#         base_url=GROQ_BASE_URL,
#         api_key=GROQ_API_KEY
#     )


# # ============================================================
# # SYSTEM PROMPT
# # ============================================================

# SYSTEM_PROMPT = """
# You are Jarvis, a personal AI assistant.

# Be concise, practical, conversational and natural.

# Rules:

# - For greetings, respond in one short sentence.
# - For simple factual questions, answer briefly.
# - Do not give long explanations unless the user asks.
# - Do not repeat the user's question.
# - Do not explain your reasoning.

# Tools:

# - You can access the user's Gmail.
# - You can access weather information.
# - You can search the web and research sources.
# - You can open YouTube.
# - When the user asks about their emails, use the Gmail tool.
# - Never claim to have accessed an email unless the Gmail tool actually returned it.

# Research:

# - When using research or web search results, rely only on information
#   provided by the tools.
# - Never invent sources, URLs, papers, authors or citations.
# - When the user asks for sources, include the actual sources returned
#   by the research tool.
# - Prefer authoritative and academic sources when available.
# """


# # ============================================================
# # PROVIDER STATUS
# # ============================================================

# def is_local_available():
#     """
#     Check whether LM Studio is currently running.
#     """

#     try:
#         local_client.models.list()
#         return True

#     except Exception:
#         return False


# # ============================================================
# # AUTO PROVIDER SELECTION
# # ============================================================

# def get_llm():

#     # --------------------------------------------------------
#     # 1. Prefer LOCAL
#     # --------------------------------------------------------

#     if is_local_available():

#         return {
#             "client": local_client,
#             "model": LOCAL_MODEL,
#             "provider": "local"
#         }

#     # --------------------------------------------------------
#     # 2. Fall back to GROQ
#     # --------------------------------------------------------

#     if groq_client:

#         return {
#             "client": groq_client,
#             "model": GROQ_MODEL,
#             "provider": "groq"
#         }

#     # --------------------------------------------------------
#     # 3. Nothing available
#     # --------------------------------------------------------

#     raise RuntimeError(
#         "No LLM provider is available. "
#         "Start LM Studio or configure GROQ_API_KEY."
#     )


# # ============================================================
# # ASK JARVIS
# # ============================================================

# def ask_jarvis(message: str, messages=None):

#     provider = get_llm()

#     client = provider["client"]
#     model = provider["model"]

#     if messages is None:

#         messages = [
#             {
#                 "role": "system",
#                 "content": SYSTEM_PROMPT
#             }
#         ]

#     messages.append({
#         "role": "user",
#         "content": message
#     })

#     response = client.chat.completions.create(
#         model=model,

#         messages=messages,

#         temperature=0.5,

#         max_tokens=128
#     )

#     return response.choices[0].message.content


# # ============================================================
# # PROVIDER INFO
# # ============================================================

# def get_provider_info():

#     provider = get_llm()

#     return provider["provider"], provider["model"]

# def stream_response(messages, tools=None):
#     """
#     Stream an LLM response token-by-token.

#     Yields:
#         {
#             "type": "text",
#             "content": "..."
#         }

#     or, when a tool is requested:
#         {
#             "type": "tool_call",
#             "tool_calls": [...]
#         }
#     """

#     provider = get_llm()

#     client = provider["client"]
#     model = provider["model"]

#     kwargs = {
#         "model": model,
#         "messages": messages,
#         "temperature": 0.2,
#         "max_tokens": 128,
#         "stream": True,
#     }

#     if tools:
#         kwargs["tools"] = tools
#         kwargs["tool_choice"] = "auto"

#     stream = client.chat.completions.create(**kwargs)

#     tool_calls = {}

#     for chunk in stream:

#         if not chunk.choices:
#             continue

#         delta = chunk.choices[0].delta

#         # ---------------------------------------------
#         # NORMAL TEXT
#         # ---------------------------------------------

#         if delta.content:
#             yield {
#                 "type": "text",
#                 "content": delta.content,
#             }

#         # ---------------------------------------------
#         # TOOL CALL
#         # ---------------------------------------------

#         if delta.tool_calls:

#             for tool_call in delta.tool_calls:

#                 index = tool_call.index

#                 if index not in tool_calls:
#                     tool_calls[index] = {
#                         "id": "",
#                         "type": "function",
#                         "function": {
#                             "name": "",
#                             "arguments": "",
#                         },
#                     }

#                 if tool_call.id:
#                     tool_calls[index]["id"] += tool_call.id

#                 if tool_call.function:

#                     if tool_call.function.name:
#                         tool_calls[index]["function"]["name"] += (
#                             tool_call.function.name
#                         )

#                     if tool_call.function.arguments:
#                         tool_calls[index]["function"]["arguments"] += (
#                             tool_call.function.arguments
#                         )

#     # ---------------------------------------------
#     # RETURN COMPLETED TOOL CALLS
#     # ---------------------------------------------

#     if tool_calls:
#         yield {
#             "type": "tool_call",
#             "tool_calls": list(tool_calls.values()),
#         }


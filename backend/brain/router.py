import json
from typing import Generator

from backend.brain.llm import SYSTEM_PROMPT, get_llm, get_provider_info
from backend.tools.tools_registry import TOOL_DEFINITIONS, execute_tool


MAX_TOOL_ROUNDS = 5
_roast_mode = False


ROAST_PROMPT = """
ROAST MODE IS ON.

Jarvis is still helpful and accurate, but now has a dry, witty, slightly
moody personality. Think clever British-style AI banter rather than a
stand-up comedian.

- Tease the user lightly when the situation invites it.
- Be playful, sarcastic and occasionally dramatic.
- Never be cruel, hateful, threatening, sexual, or genuinely insulting.
- Never roast sensitive personal traits or protected characteristics.
- Never let the joke obscure the actual answer or action.
- Keep roasts short; do not turn every sentence into a joke.
- If the user is stressed or asks for serious help, dial the humor down.
- Do not announce "roast mode" in every response.
- Example tone: "Done. Because apparently clicking the button was too
  much responsibility for today."
"""


def set_roast_mode(enabled: bool):
    """Enable or disable Jarvis's playful roast personality."""
    global _roast_mode
    _roast_mode = bool(enabled)
    print(f"[JARVIS] Roast mode: {'ON' if _roast_mode else 'OFF'}")


def is_roast_mode():
    return _roast_mode


def _build_messages(message: str, conversation=None):
    system_prompt = SYSTEM_PROMPT
    if _roast_mode:
        system_prompt += "\n\n" + ROAST_PROMPT

    messages = [{"role": "system", "content": system_prompt}]
    if conversation:
        messages.extend(conversation)
    messages.append({"role": "user", "content": message})
    return messages


def _clean_tool_arguments(arguments):
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


def get_router_status():
    status = get_provider_info()
    status["roast_mode"] = _roast_mode
    return status


def process_request(user_input: str, conversation=None):
    messages = _build_messages(user_input, conversation)

    for _ in range(MAX_TOOL_ROUNDS):
        client, model = get_llm()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7 if _roast_mode else 0.5,
            max_tokens=128,
        )

        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:
            content = assistant_message.content or ""
            if conversation is not None:
                conversation.append({"role": "user", "content": user_input})
                conversation.append({"role": "assistant", "content": content})
            return {"type": "text", "content": content}

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
                    },
                }
                for call in assistant_message.tool_calls
            ],
        })

        for call in assistant_message.tool_calls:
            tool_name = call.function.name
            arguments = _clean_tool_arguments(call.function.arguments)
            print(f"[Tool] {tool_name}({arguments})")

            try:
                result = execute_tool(tool_name, arguments)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    return {"type": "text", "content": "I couldn't complete that request."}


def process_request_stream(user_input: str, conversation=None) -> Generator[dict, None, None]:
    messages = _build_messages(user_input, conversation)

    for _ in range(MAX_TOOL_ROUNDS):
        client, model = get_llm()
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7 if _roast_mode else 0.5,
            max_tokens=128,
            stream=True,
        )

        full_response = ""
        tool_calls = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                full_response += delta.content
                yield {"type": "text", "content": delta.content}

            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index
                    if index not in tool_calls:
                        tool_calls[index] = {"id": "", "name": "", "arguments": ""}
                    if tool_call.id:
                        tool_calls[index]["id"] = tool_call.id
                    if tool_call.function:
                        if tool_call.function.name:
                            tool_calls[index]["name"] += tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls[index]["arguments"] += tool_call.function.arguments

        if not tool_calls:
            if conversation is not None:
                conversation.append({"role": "user", "content": user_input})
                conversation.append({"role": "assistant", "content": full_response})
            yield {"type": "done"}
            return

        assistant_tool_calls = []
        for call in tool_calls.values():
            assistant_tool_calls.append({
                "id": call["id"],
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["arguments"],
                },
            })

        messages.append({
            "role": "assistant",
            "content": full_response or None,
            "tool_calls": assistant_tool_calls,
        })

        for call in tool_calls.values():
            tool_name = call["name"]
            arguments = _clean_tool_arguments(call["arguments"])
            print(f"[Tool] {tool_name}({arguments})")
            yield {"type": "tool", "tool": tool_name, "arguments": arguments}

            try:
                result = execute_tool(tool_name, arguments)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    yield {"type": "error", "content": "I couldn't complete that request."}

from typing import Optional


class ConversationManager:
    """
    Manages Jarvis's short-term conversation history.

    This is session memory:
    - It exists while Jarvis is running.
    - It stores recent messages.
    - It provides context for follow-up questions.
    - It does NOT permanently remember the user.
    """

    def __init__(self, max_messages: int = 20):
        self.messages = []
        self.max_messages = max_messages

    # ========================================================
    # ADD MESSAGE
    # ========================================================

    def add_message(self, role: str, content: str):
        """
        Add a message to the current conversation.
        """

        self.messages.append({
            "role": role,
            "content": content
        })

        self._trim_history()

    # ========================================================
    # ADD TOOL CALL
    # ========================================================

    def add_tool_message(
        self,
        tool_call_id: str,
        content: str
    ):
        """
        Store the result returned by a tool.
        """

        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        })

        self._trim_history()

    # ========================================================
    # GET MESSAGES
    # ========================================================

    def get_messages(self):
        """
        Return the current conversation history.
        """

        return self.messages.copy()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self):
        """
        Clear the current session.
        """

        self.messages.clear()

    # ========================================================
    # HISTORY LIMIT
    # ========================================================

    def _trim_history(self):
        """
        Keep only the most recent messages.

        This prevents the prompt from growing indefinitely,
        which helps reduce latency and token usage.
        """

        if len(self.messages) > self.max_messages:

            excess = (
                len(self.messages)
                - self.max_messages
            )

            del self.messages[:excess]

    # ========================================================
    # LAST MESSAGE
    # ========================================================

    def last_message(self) -> Optional[dict]:
        """
        Return the most recent message.
        """

        if not self.messages:
            return None

        return self.messages[-1]
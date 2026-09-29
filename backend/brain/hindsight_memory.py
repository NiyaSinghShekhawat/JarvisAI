import os
from typing import Any

from dotenv import load_dotenv
from hindsight_client import Hindsight


# This module is imported before llm.py in the router, so load .env here
# before reading Hindsight configuration.
load_dotenv()

HINDSIGHT_API_URL = os.getenv("HINDSIGHT_API_URL", "http://localhost:8888")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "jarvis-user")


class HindsightMemory:
    """Thin wrapper around Hindsight for Jarvis long-term memory."""

    def __init__(
        self,
        api_url: str = HINDSIGHT_API_URL,
        api_key: str | None = HINDSIGHT_API_KEY,
        bank_id: str = HINDSIGHT_BANK_ID,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.bank_id = bank_id

        kwargs = {"base_url": api_url}
        if api_key:
            kwargs["api_key"] = api_key

        self.client = Hindsight(**kwargs)

    def recall(self, query: str) -> list[str]:
        """Recall memories relevant to the current request.

        Memory is optional: if the Hindsight service is unavailable, Jarvis
        should continue normally instead of failing the user's request.
        """
        if not query.strip():
            return []

        try:
            result = self.client.recall(
                bank_id=self.bank_id,
                query=query,
            )
            return self._extract_memories(result)
        except Exception as exc:
            print(f"[Memory] Hindsight recall unavailable: {exc}")
            return []

    def retain_turn(self, user_input: str, assistant_response: str):
        """Store one completed user/assistant turn for long-term extraction."""
        user_input = (user_input or "").strip()
        assistant_response = (assistant_response or "").strip()

        if not user_input or not assistant_response:
            return

        content = (
            "Conversation with Jarvis:\n"
            f"User: {user_input}\n"
            f"Jarvis: {assistant_response}"
        )

        try:
            self.client.retain(
                bank_id=self.bank_id,
                content=content,
            )
        except Exception as exc:
            print(f"[Memory] Hindsight retain unavailable: {exc}")

    @staticmethod
    def _extract_memories(result: Any) -> list[str]:
        """Normalize Hindsight client responses without coupling Jarvis to one SDK shape."""
        if result is None:
            return []

        if isinstance(result, dict):
            candidates = (
                result.get("results")
                or result.get("memories")
                or result.get("items")
                or []
            )
        else:
            candidates = getattr(result, "results", None) or getattr(
                result, "memories", None
            ) or result

        if not isinstance(candidates, (list, tuple)):
            candidates = [candidates]

        memories: list[str] = []
        for item in candidates:
            if item is None:
                continue

            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("memory")
                    or item.get("fact")
                    or ""
                )
            else:
                text = (
                    getattr(item, "text", None)
                    or getattr(item, "content", None)
                    or getattr(item, "memory", None)
                    or getattr(item, "fact", None)
                    or str(item)
                )

            text = str(text).strip()
            if text and text not in memories:
                memories.append(text)

        return memories[:8]


memory = HindsightMemory()

import json
from pathlib import Path


class MemoryManager:
    """
    Manages Jarvis's persistent memories.

    Unlike ConversationManager, these memories survive
    when Jarvis is restarted.
    """

    def __init__(self, memory_file=None):

        if memory_file is None:

            base_dir = Path(__file__).resolve().parents[2]

            memory_file = (
                base_dir
                / "data"
                / "memory.json"
            )

        self.memory_file = Path(memory_file)

        self.memory_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.memories = self._load()

    # ========================================================
    # LOAD
    # ========================================================

    def _load(self):
        """
        Load persistent memories from disk.
        """

        if not self.memory_file.exists():
            return []

        try:

            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            if isinstance(data, list):
                return data

        except (
            json.JSONDecodeError,
            OSError
        ):
            pass

        return []

    # ========================================================
    # SAVE
    # ========================================================

    def _save(self):
        """
        Save memories to disk.
        """

        with open(
            self.memory_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.memories,
                file,
                indent=4,
                ensure_ascii=False
            )

    # ========================================================
    # ADD MEMORY
    # ========================================================

    def add_memory(
        self,
        content: str,
        category: str = "general"
    ):
        """
        Store a new persistent memory.
        """

        memory = {
            "content": content,
            "category": category
        }

        self.memories.append(memory)

        self._save()

    # ========================================================
    # GET MEMORIES
    # ========================================================

    def get_memories(
        self,
        category: str = None
    ):
        """
        Return stored memories.

        If category is supplied, only memories belonging
        to that category are returned.
        """

        if category is None:
            return self.memories.copy()

        return [
            memory
            for memory in self.memories
            if memory.get("category") == category
        ]

    # ========================================================
    # SEARCH
    # ========================================================

    def search(self, query: str):
        """
        Very simple keyword-based memory search for now.
        """

        query_words = query.lower().split()

        results = []

        for memory in self.memories:

            content = memory.get(
                "content",
                ""
            ).lower()

            if any(
                word in content
                for word in query_words
            ):
                results.append(memory)

        return results

    # ========================================================
    # DELETE
    # ========================================================

    def delete_memory(self, index: int):

        if 0 <= index < len(self.memories):

            self.memories.pop(index)

            self._save()

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def clear(self):

        self.memories.clear()

        self._save()
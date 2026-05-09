"""In-memory implementation of NLPPort for testing."""

from typing import Any


class FakeNLPAdapter:
    """Fake NLP adapter that returns preconfigured extraction results."""

    def __init__(self, result: dict[str, Any] | None = None):
        self.result = result
        self.calls: list[tuple[str, str]] = []

    async def extract(self, word: str, sentence: str) -> dict[str, Any] | None:
        self.calls.append((word, sentence))
        return self.result

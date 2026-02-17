"""In-memory implementation of DictionaryPort for testing."""


class FakeDictionaryAdapter:
    """Fake dictionary adapter that returns preconfigured responses."""

    def __init__(self, entries: list[dict] | None = None):
        self.entries = entries
        self.last_word: str | None = None
        self.last_language: str | None = None

    async def fetch(self, word: str, language: str) -> list[dict] | None:
        self.last_word = word
        self.last_language = language
        return self.entries

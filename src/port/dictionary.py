"""Dictionary port — outbound interface for dictionary data sources."""

from typing import Protocol


class DictionaryPort(Protocol):
    """Port for fetching dictionary entries from an external source.

    Returns a list of entry dicts, each with keys like
    'partOfSpeech', 'senses', 'pronunciations', 'forms'.
    """

    async def fetch(self, word: str, language: str) -> list[dict] | None: ...

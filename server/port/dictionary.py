"""Dictionary port — outbound interface for dictionary data sources."""

from typing import Any, Protocol

from domain.model.vocabulary import GrammaticalInfo, SenseResult


class DictionaryPort(Protocol):
    """Port for fetching dictionary entries.

    fetch() returns raw entry dicts from the dictionary source.
    build_sense_listing() / get_sense() / extract_grammar()
    encapsulate all entry-structure knowledge so that the service
    layer only deals with domain types (SenseResult, GrammaticalInfo).
    """

    async def fetch(self, word: str, language: str) -> list[dict] | None: ...

    def build_sense_listing(self, entries: list[dict[str, Any]]) -> str | None:
        """Format entries for LLM prompt. Returns None if trivial (single sense)."""
        ...

    def get_sense(
        self, entries: list[dict[str, Any]], label: str,
    ) -> SenseResult:
        """Return the definition and examples for the selected sense."""
        ...

    def extract_grammar(
        self, entries: list[dict[str, Any]], label: str, language: str,
    ) -> GrammaticalInfo: ...

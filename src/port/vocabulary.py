"""Port for vocabulary aggregate queries."""

from typing import Protocol

from domain.model.vocabulary import VocabularyCount


class VocabularyPort(Protocol):
    """Protocol for vocabulary aggregate queries (read-only).

    Separated from VocabularyRepository (CRUD) to clarify intent:
    repository handles individual entry persistence,
    this port handles cross-entry read queries.
    """

    def count_by_lemma(
        self,
        language: str | None = None,
        user_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VocabularyCount]:
        """Aggregate vocabulary counts grouped by language + lemma, sorted by count descending."""
        ...

    def find_lemmas(
        self,
        user_id: str,
        language: str,
        levels: list[str] | None = None,
        limit: int = 50,
    ) -> list[str]:
        """Get distinct lemmas sorted by frequency (desc) then recency (desc)."""
        ...

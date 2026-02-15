"""Port for vocabulary data access."""

from typing import Protocol

from domain.model.vocabulary import GrammaticalInfo, Vocabulary, VocabularyCount


class VocabularyRepository(Protocol):
    """Protocol for individual vocabulary entry data access (CRUD + primitive queries)."""

    def save(
        self,
        article_id: str,
        word: str,
        lemma: str,
        definition: str,
        sentence: str,
        language: str,
        related_words: list[str] | None = None,
        span_id: str | None = None,
        user_id: str | None = None,
        grammar: GrammaticalInfo | None = None,
    ) -> str | None:
        """Save a new vocabulary entry. Returns inserted ID, or None on failure."""
        ...

    def get_by_id(self, vocabulary_id: str) -> Vocabulary | None:
        """Get a single vocabulary entry by ID."""
        ...

    def find(
        self,
        article_id: str | None = None,
        user_id: str | None = None,
        lemma: str | None = None,
    ) -> list[Vocabulary]:
        """Get vocabularies filtered by article_id, user_id, and/or lemma.

        Lemma matching is case-insensitive. Sorted by created_at descending.
        """
        ...

    def update_span_id(self, vocabulary_id: str, span_id: str) -> None:
        """Update span_id of an existing vocabulary entry."""
        ...

    def delete(self, vocabulary_id: str) -> bool:
        """Delete a vocabulary entry. Returns True if deleted, False if not found."""
        ...

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

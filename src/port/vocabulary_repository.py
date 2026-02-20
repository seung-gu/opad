"""Port for vocabulary data access."""

from typing import Protocol

from domain.model.vocabulary import Vocabulary


class VocabularyRepository(Protocol):
    """Protocol for individual vocabulary entry data access (CRUD + primitive queries)."""

    def save(self, vocab: Vocabulary) -> str | None:
        """Save a vocabulary entry, skipping duplicates based on identity.

        Uses vocab.identity to check for existing entries.
        Returns existing ID if duplicate, new ID if inserted, None on failure.
        """
        ...

    def find_duplicate(self, vocab: Vocabulary) -> Vocabulary | None:
        """Find an existing entry with the same business identity."""
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

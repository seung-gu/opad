"""Vocabulary domain models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GrammaticalInfo:
    """Optional grammatical metadata for a vocabulary entry."""
    pos: str | None = None
    gender: str | None = None
    phonetics: str | None = None
    conjugations: dict | None = None
    level: str | None = None
    examples: list[str] | None = None


@dataclass
class Vocabulary:
    """A single vocabulary entry saved by a user."""

    IDENTITY_FIELDS = ('user_id', 'article_id', 'lemma')

    id: str
    article_id: str
    word: str
    lemma: str
    definition: str
    sentence: str
    language: str
    created_at: datetime
    related_words: list[str] | None = None
    span_id: str | None = None
    user_id: str | None = None
    grammar: GrammaticalInfo = field(default_factory=GrammaticalInfo)

    @property
    def identity(self) -> dict:
        """Business identity — fields that define uniqueness."""
        return {f: getattr(self, f) for f in self.IDENTITY_FIELDS}


@dataclass
class VocabularyCount:
    """Aggregated vocabulary grouped by language + lemma.

    Represents the result of get_vocabulary_counts() — the most recent
    entry for each unique (language, lemma) pair, plus occurrence count
    and list of article IDs where this lemma appeared.
    """
    vocabulary: Vocabulary
    count: int
    article_ids: list[str] = field(default_factory=list)

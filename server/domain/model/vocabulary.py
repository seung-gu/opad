"""Vocabulary domain models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from domain.model.errors import PermissionDeniedError


@dataclass(frozen=True)
class GrammaticalInfo:
    """Optional grammatical metadata for a vocabulary entry."""
    pos: str | None = None
    gender: str | None = None
    phonetics: str | None = None
    conjugations: dict | None = None
    examples: list[str] | None = None


@dataclass
class SenseResult:
    """Selected sense from dictionary entries."""
    definition: str = ""
    examples: list[str] | None = None


@dataclass(frozen=True)
class LookupResult:
    """Immutable result of a dictionary lookup (Value Object).

    Returned by dictionary_service.lookup() to provide a typed contract
    instead of a raw dict.
    """
    lemma: str
    definition: str
    related_words: list[str] | None = None
    level: str | None = None
    grammar: GrammaticalInfo = field(default_factory=GrammaticalInfo)


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
    level: str | None = None
    span_id: str | None = None
    user_id: str | None = None
    grammar: GrammaticalInfo = field(default_factory=GrammaticalInfo)

    @staticmethod
    def create(
        article_id: str,
        word: str,
        lemma: str,
        definition: str,
        sentence: str,
        language: str,
        related_words: list[str] | None = None,
        span_id: str | None = None,
        user_id: str | None = None,
        level: str | None = None,
        grammar: GrammaticalInfo | None = None,
    ) -> 'Vocabulary':
        """Factory method — same pattern as Article.create()."""
        return Vocabulary(
            id=str(uuid.uuid4()),
            article_id=article_id,
            word=word,
            lemma=lemma,
            definition=definition,
            sentence=sentence,
            language=language,
            created_at=datetime.now(timezone.utc),
            related_words=related_words,
            level=level,
            span_id=span_id,
            user_id=user_id,
            grammar=grammar or GrammaticalInfo(),
        )

    def check_ownership(self, user_id: str) -> None:
        """Verify ownership. Raises PermissionDeniedError on mismatch."""
        if self.user_id != user_id:
            raise PermissionDeniedError("Not authorized to access this vocabulary")

    @property
    def identity(self) -> dict:
        """Business identity — fields that define uniqueness."""
        return {f: getattr(self, f) for f in self.IDENTITY_FIELDS}


@dataclass
class VocabularyCount:
    """Aggregated vocabulary grouped by language + lemma.

    Represents the result of count_by_lemma() — the most recent
    entry for each unique (language, lemma) pair, plus occurrence count
    and list of article IDs where this lemma appeared.
    """
    vocabulary: Vocabulary
    count: int
    article_ids: list[str] = field(default_factory=list)

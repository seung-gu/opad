"""Vocabulary service — domain object creation + repository orchestration."""

import uuid
from datetime import datetime, timezone

from domain.model.vocabulary import GrammaticalInfo, Vocabulary
from port.vocabulary_repository import VocabularyRepository


def save(
    repo: VocabularyRepository,
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
) -> Vocabulary | None:
    """Create a Vocabulary domain object and save it.

    Returns the saved Vocabulary (or existing one if duplicate).
    Returns None on failure.
    """
    vocab = Vocabulary(
        id=str(uuid.uuid4()),
        article_id=article_id,
        word=word,
        lemma=lemma,
        definition=definition,
        sentence=sentence,
        language=language,
        created_at=datetime.now(timezone.utc),
        related_words=related_words,
        span_id=span_id,
        user_id=user_id,
        grammar=grammar or GrammaticalInfo(),
    )
    vocab_id = repo.save(vocab)
    if not vocab_id:
        return None
    return repo.get_by_id(vocab_id)

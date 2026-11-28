"""Vocabulary query — the words a learner already knows."""

from domain.model.cefr import CEFRLevel, Level
from port.outbound.repository.vocabulary import VocabularyRepository

_KNOWN_WORDS_LIMIT = 50


def find_known_words(
    user_id: str | None,
    language: str,
    level: Level | None,
    vocab: VocabularyRepository | None,
) -> list[str]:
    """The learner's most-saved words, from A1 up to one level above the target level."""
    if not user_id or not language or not vocab:
        return []

    words = vocab.find_lemmas(
        user_id=user_id,
        language=language,
        levels=CEFRLevel.range(CEFRLevel.next(level)),
        limit=_KNOWN_WORDS_LIMIT,
    )
    return words if words else []

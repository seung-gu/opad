"""Vocabulary service — business logic for the user's word book.

Operates on the vocabulary collection as a whole (statistics, lemma lists),
as opposed to VocabularyRepository which handles individual entry CRUD.
"""

from domain.model.vocabulary import GrammaticalInfo, VocabularyCount
from port.vocabulary_repository import VocabularyRepository

# ── CEFR level business rules ────────────────────────────────

CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']


def get_allowed_vocab_levels(target_level: str, max_above: int = 1) -> list[str]:
    """Get allowed vocabulary levels for a target article level.

    Args:
        target_level: Target CEFR level (A1-C2)
        max_above: Maximum levels above target to allow (default: 1)

    Returns:
        List of allowed CEFR levels. Words at these levels can be used.
        Returns all levels if target_level is invalid.

    Example:
        get_allowed_vocab_levels('A2', max_above=1) → ['A1', 'A2', 'B1']
        get_allowed_vocab_levels('B1', max_above=1) → ['A1', 'A2', 'B1', 'B2']
    """
    if not target_level or not target_level.strip():
        return CEFR_LEVELS
    target_upper = target_level.upper()
    if target_upper not in CEFR_LEVELS:
        return CEFR_LEVELS  # Allow all if invalid

    target_index = CEFR_LEVELS.index(target_upper)
    # Ensure we always include at least up to target level (handle negative max_above safely)
    max_index = max(target_index, min(target_index + max_above, len(CEFR_LEVELS) - 1))
    return CEFR_LEVELS[:max_index + 1]


def save_vocabulary(
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
) -> str | None:
    """Save a vocabulary entry, returning existing ID if duplicate.

    Duplicate = same user + article + lemma (case-insensitive).
    If duplicate found and span_id differs, updates span_id.
    """
    existing = repo.find(article_id=article_id, user_id=user_id, lemma=lemma)
    if existing:
        entry = existing[0]
        normalized_span_id = span_id if span_id and span_id.strip() else None
        if normalized_span_id and entry.span_id != normalized_span_id:
            repo.update_span_id(entry.id, normalized_span_id)
        return entry.id
    return repo.save(
        article_id=article_id,
        word=word,
        lemma=lemma,
        definition=definition,
        sentence=sentence,
        language=language,
        related_words=related_words,
        span_id=span_id,
        user_id=user_id,
        grammar=grammar,
    )


def get_counts(
    repo: VocabularyRepository,
    language: str | None = None,
    user_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[VocabularyCount]:
    """Get vocabulary counts grouped by language + lemma."""
    return repo.count_by_lemma(language, user_id, skip, limit)


def get_user_lemmas(
    repo: VocabularyRepository,
    user_id: str,
    language: str,
    target_level: str | None = None,
    limit: int = 50,
) -> list[str]:
    """Get user's learned lemmas, filtered by CEFR level.

    Args:
        repo: Vocabulary repository for data access
        user_id: User ID
        language: Target language
        target_level: Target CEFR level. If provided, filters out vocab
                     more than 1 level above target.
        limit: Maximum number of lemmas (clamped to [1, 1000])
    """
    limit = max(1, min(limit, 1000))
    levels = get_allowed_vocab_levels(target_level) if target_level else None
    return repo.find_lemmas(user_id, language, levels=levels, limit=limit)

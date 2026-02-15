"""In-memory implementation of VocabularyRepository for testing."""

import uuid
from datetime import datetime, timezone

from domain.model.vocabulary import GrammaticalInfo, Vocabulary, VocabularyCount


class FakeVocabularyRepository:
    def __init__(self):
        self.store: dict[str, Vocabulary] = {}

    # ── CRUD ──────────────────────────────────────────────────

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
        """Save a new vocabulary entry."""
        normalized_span_id = span_id if span_id and span_id.strip() else None
        vocab_id = str(uuid.uuid4())
        self.store[vocab_id] = Vocabulary(
            id=vocab_id,
            article_id=article_id,
            word=word,
            lemma=lemma,
            definition=definition,
            sentence=sentence,
            language=language,
            created_at=datetime.now(timezone.utc),
            related_words=related_words or [],
            span_id=normalized_span_id,
            user_id=user_id,
            grammar=grammar or GrammaticalInfo(),
        )
        return vocab_id

    def get_by_id(self, vocabulary_id: str) -> Vocabulary | None:
        return self.store.get(vocabulary_id)

    def find(
        self,
        article_id: str | None = None,
        user_id: str | None = None,
        lemma: str | None = None,
    ) -> list[Vocabulary]:
        results = list(self.store.values())
        if article_id:
            results = [v for v in results if v.article_id == article_id]
        if user_id:
            results = [v for v in results if v.user_id == user_id]
        if lemma:
            results = [v for v in results if v.lemma.lower() == lemma.lower()]
        return sorted(results, key=lambda v: v.created_at, reverse=True)

    def update_span_id(self, vocabulary_id: str, span_id: str) -> None:
        if vocabulary_id in self.store:
            vocab = self.store[vocabulary_id]
            # dataclass — direct attribute assignment
            vocab.span_id = span_id

    def delete(self, vocabulary_id: str) -> bool:
        if vocabulary_id in self.store:
            del self.store[vocabulary_id]
            return True
        return False

    # ── aggregate queries ─────────────────────────────────────

    def count_by_lemma(
        self,
        language: str | None = None,
        user_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VocabularyCount]:
        filtered = list(self.store.values())
        if language:
            filtered = [v for v in filtered if v.language == language]
        if user_id:
            filtered = [v for v in filtered if v.user_id == user_id]

        # Group by (language, lemma)
        groups: dict[tuple[str, str], list[Vocabulary]] = {}
        for v in filtered:
            key = (v.language, v.lemma)
            groups.setdefault(key, []).append(v)

        result = []
        for (lang, lemma), vocabs in groups.items():
            newest = max(vocabs, key=lambda v: v.created_at)
            article_ids = list({v.article_id for v in vocabs})
            result.append(VocabularyCount(
                vocabulary=newest,
                count=len(vocabs),
                article_ids=article_ids,
            ))

        # Sort by count desc, then lemma asc
        result.sort(key=lambda vc: (-vc.count, vc.vocabulary.lemma))
        return result[skip:skip + limit]

    def find_lemmas(
        self,
        user_id: str,
        language: str,
        levels: list[str] | None = None,
        limit: int = 50,
    ) -> list[str]:
        filtered = [
            v for v in self.store.values()
            if v.user_id == user_id and v.language == language
        ]
        if levels:
            filtered = [v for v in filtered if v.grammar and v.grammar.level in levels]

        # Group by lemma: count + max created_at
        lemma_stats: dict[str, dict] = {}
        for v in filtered:
            if v.lemma in lemma_stats:
                lemma_stats[v.lemma]['count'] += 1
                lemma_stats[v.lemma]['max_created_at'] = max(
                    lemma_stats[v.lemma]['max_created_at'], v.created_at,
                )
            else:
                lemma_stats[v.lemma] = {'count': 1, 'max_created_at': v.created_at}

        # Sort by count desc, then recency desc
        sorted_lemmas = sorted(
            lemma_stats.items(),
            key=lambda item: (-item[1]['count'], -item[1]['max_created_at'].timestamp()),
        )
        return [lemma for lemma, _ in sorted_lemmas[:limit]]

"""MongoDB implementation of VocabularyRepository."""

import re
from datetime import datetime, timezone
from logging import getLogger

from pymongo.database import Database
from pymongo.errors import PyMongoError

from adapter.mongodb import VOCABULARY_COLLECTION_NAME
from domain.model.vocabulary import GrammaticalInfo, Vocabulary, VocabularyCount

logger = getLogger(__name__)


class MongoVocabularyRepository:
    def __init__(self, db: Database):
        self.collection = db[VOCABULARY_COLLECTION_NAME]

    # ── indexes ────────────────────────────────────────────────

    def ensure_indexes(self) -> bool:
        """Create indexes for vocabularies collection."""
        from adapter.mongodb.indexes import create_index_safe

        try:
            create_index_safe(self.collection, [('user_id', 1)], 'idx_vocab_user_id', sparse=True)
            create_index_safe(self.collection, [('user_id', 1), ('article_id', 1)], 'idx_vocab_user_article')
            create_index_safe(self.collection, [('user_id', 1), ('language', 1)], 'idx_vocab_user_language')
            create_index_safe(self.collection, [('created_at', -1)], 'idx_vocab_created_at')
            return True
        except Exception as e:
            logger.error("Failed to create vocabularies indexes", extra={"error": str(e)})
            return False

    # ── mapping ───────────────────────────────────────────────

    def _to_domain(self, doc: dict) -> Vocabulary:
        """Convert a flat MongoDB document to a Vocabulary domain model.

        MongoDB stores grammar fields (pos, gender, …) at the top level,
        but the domain model nests them inside GrammaticalInfo.
        """
        return Vocabulary(
            id=doc['_id'],
            article_id=doc['article_id'],
            word=doc['word'],
            lemma=doc['lemma'],
            definition=doc['definition'],
            sentence=doc['sentence'],
            language=doc['language'],
            created_at=doc['created_at'],
            related_words=doc.get('related_words'),
            level=doc.get('level'),
            span_id=doc.get('span_id'),
            user_id=doc.get('user_id'),
            grammar=GrammaticalInfo(
                pos=doc.get('pos'),
                gender=doc.get('gender'),
                phonetics=doc.get('phonetics'),
                conjugations=doc.get('conjugations'),
                examples=doc.get('examples'),
            )
        )

    # ── CRUD ──────────────────────────────────────────────────

    def find_duplicate(self, vocab: Vocabulary) -> Vocabulary | None:
        """Find an existing entry with the same business identity."""
        try:
            doc = self.collection.find_one(vocab.identity)
            return self._to_domain(doc) if doc else None
        except PyMongoError as e:
            logger.error("Failed to find duplicate", extra={"lemma": vocab.lemma, "error": str(e)})
            return None

    def save(self, vocab: Vocabulary) -> str | None:
        """Save a vocabulary entry, skipping duplicates based on identity.

        Uses vocab.identity to check for existing entries.
        If duplicate found, updates span_id if changed and returns existing ID.
        """
        try:
            existing = self.find_duplicate(vocab)
            if existing:
                return existing.id

            g = vocab.grammar or GrammaticalInfo()
            doc = {
                '_id': vocab.id,
                'article_id': vocab.article_id,
                'word': vocab.word,
                'lemma': vocab.lemma,
                'definition': vocab.definition,
                'sentence': vocab.sentence,
                'language': vocab.language,
                'related_words': vocab.related_words or [],
                'span_id': vocab.span_id if vocab.span_id and vocab.span_id.strip() else None,
                'user_id': vocab.user_id,
                'pos': g.pos,
                'gender': g.gender,
                'phonetics': g.phonetics,
                'conjugations': g.conjugations,
                'level': vocab.level,
                'examples': g.examples,
                'created_at': vocab.created_at,
                'updated_at': vocab.created_at,
            }

            self.collection.insert_one(doc)
            logger.info("Vocabulary saved", extra={"vocabularyId": doc['_id'], "lemma": vocab.lemma})
            return doc['_id']
        except PyMongoError as e:
            logger.error("Failed to save vocabulary", extra={"lemma": vocab.lemma, "error": str(e)})
            return None

    def get_by_id(self, vocabulary_id: str) -> Vocabulary | None:
        try:
            doc = self.collection.find_one({'_id': vocabulary_id})
            return self._to_domain(doc) if doc else None
        except PyMongoError as e:
            logger.error("Failed to get vocabulary", extra={"vocabularyId": vocabulary_id, "error": str(e)})
            return None

    def find(
        self,
        article_id: str | None = None,
        user_id: str | None = None,
        lemma: str | None = None,
    ) -> list[Vocabulary]:
        try:
            query: dict = {}
            if article_id:
                query['article_id'] = article_id
            if user_id:
                query['user_id'] = user_id
            if lemma:
                escaped = re.escape(lemma)
                query['lemma'] = {'$regex': f'^{escaped}$', '$options': 'i'}

            return [self._to_domain(doc) for doc in self.collection.find(query).sort('created_at', -1)]
        except PyMongoError as e:
            logger.error("Failed to find vocabularies", extra={"error": str(e)})
            return []

    def update_span_id(self, vocabulary_id: str, span_id: str) -> None:
        try:
            self.collection.update_one(
                {'_id': vocabulary_id},
                {'$set': {'span_id': span_id, 'updated_at': datetime.now(timezone.utc)}},
            )
        except PyMongoError as e:
            logger.error("Failed to update span_id", extra={"vocabularyId": vocabulary_id, "error": str(e)})

    def delete(self, vocabulary_id: str) -> bool:
        try:
            result = self.collection.delete_one({'_id': vocabulary_id})
            if result.deleted_count == 0:
                logger.warning("Vocabulary not found for deletion", extra={"vocabularyId": vocabulary_id})
                return False
            logger.info("Vocabulary deleted", extra={"vocabularyId": vocabulary_id})
            return True
        except PyMongoError as e:
            logger.error("Failed to delete vocabulary", extra={"vocabularyId": vocabulary_id, "error": str(e)})
            return False

    # ── aggregate queries (used by service layer) ─────────────

    def count_by_lemma(
        self,
        language: str | None = None,
        user_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VocabularyCount]:
        try:
            pipeline: list[dict] = []

            match: dict = {}
            if language:
                match['language'] = language
            if user_id:
                match['user_id'] = user_id
            if match:
                pipeline.append({'$match': match})

            pipeline.append({'$sort': {'created_at': -1}})

            pipeline.append({
                '$group': {
                    '_id': {'language': '$language', 'lemma': '$lemma'},
                    'count': {'$sum': 1},
                    'article_ids': {'$addToSet': '$article_id'},
                    'vocabulary_id': {'$first': '$_id'},
                    'article_id': {'$first': '$article_id'},
                    'definition': {'$first': '$definition'},
                    'sentence': {'$first': '$sentence'},
                    'word': {'$first': '$word'},
                    'created_at': {'$first': '$created_at'},
                    'related_words': {'$first': '$related_words'},
                    'span_id': {'$first': '$span_id'},
                    'user_id': {'$first': '$user_id'},
                    'pos': {'$first': '$pos'},
                    'gender': {'$first': '$gender'},
                    'phonetics': {'$first': '$phonetics'},
                    'conjugations': {'$first': '$conjugations'},
                    'level': {'$first': '$level'},
                    'examples': {'$first': '$examples'},
                },
            })

            pipeline.append({'$sort': {'count': -1, '_id.lemma': 1}})

            if skip > 0:
                pipeline.append({'$skip': skip})
            if limit > 0:
                pipeline.append({'$limit': limit})

            result = []
            for doc in self.collection.aggregate(pipeline):
                vocab = Vocabulary(
                    id=str(doc.get('vocabulary_id', '')),
                    article_id=doc.get('article_id', ''),
                    word=doc.get('word', ''),
                    lemma=doc['_id']['lemma'],
                    definition=doc.get('definition', ''),
                    sentence=doc.get('sentence', ''),
                    language=doc['_id']['language'],
                    created_at=doc.get('created_at', datetime.now(timezone.utc)),
                    related_words=doc.get('related_words'),
                    level=doc.get('level'),
                    span_id=doc.get('span_id'),
                    user_id=doc.get('user_id'),
                    grammar=GrammaticalInfo(
                        pos=doc.get('pos'),
                        gender=doc.get('gender'),
                        phonetics=doc.get('phonetics'),
                        conjugations=doc.get('conjugations'),
                        examples=doc.get('examples'),
                    ),
                )
                result.append(VocabularyCount(
                    vocabulary=vocab,
                    count=doc['count'],
                    article_ids=doc.get('article_ids', []),
                ))
            return result
        except PyMongoError as e:
            logger.error("Failed to count vocabularies", extra={"error": str(e)})
            return []

    def find_lemmas(
        self,
        user_id: str,
        language: str,
        levels: list[str] | None = None,
        limit: int = 50,
    ) -> list[str]:
        try:
            match_filter: dict = {'user_id': user_id, 'language': language}
            if levels:
                match_filter['level'] = {'$in': levels}

            pipeline = [
                {'$match': match_filter},
                {'$group': {'_id': '$lemma', 'count': {'$sum': 1}, 'max_created_at': {'$max': '$created_at'}}},
                {'$sort': {'count': -1, 'max_created_at': -1}},
                {'$limit': limit},
                {'$project': {'_id': 0, 'lemma': '$_id'}},
            ]

            return [doc['lemma'] for doc in self.collection.aggregate(pipeline)]
        except PyMongoError as e:
            logger.error("Failed to find lemmas", extra={"userId": user_id, "error": str(e)})
            return []

"""MongoDB implementation of ArticleRepository."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from logging import getLogger

from pymongo.database import Database
from pymongo.errors import PyMongoError

from adapter.mongodb import COLLECTION_NAME
from domain.model.article import (
    Article, ArticleInputs, ArticleStatus, Articles,
    SourceInfo, EditRecord,
)

logger = getLogger(__name__)


class MongoArticleRepository:
    def __init__(self, db: Database):
        self.collection = db[COLLECTION_NAME]

    # ── indexes ──────────────────────────────────────────────

    def ensure_indexes(self) -> bool:
        """Create indexes for articles collection."""
        from adapter.mongodb.indexes import create_index_safe

        try:
            create_index_safe(self.collection, [('created_at', -1)], 'idx_created_at_desc')
            create_index_safe(self.collection, [('user_id', 1)], 'idx_user_id', sparse=True)
            create_index_safe(self.collection, [
                ('user_id', 1),
                ('inputs.language', 1),
                ('inputs.level', 1),
                ('inputs.length', 1),
                ('inputs.topic', 1),
                ('created_at', -1),
            ], 'idx_duplicate_detection')
            return True
        except Exception as e:
            logger.error("Failed to create articles indexes", extra={"error": str(e)})
            return False

    # ── helpers ──────────────────────────────────────────────

    def _to_domain(self, doc: dict) -> Article:
        """Convert MongoDB document to Article domain model."""
        source = None
        if doc.get('source'):
            source = SourceInfo(**doc['source'])

        edit_history = []
        for rec in doc.get('edit_history', []):
            edit_history.append(EditRecord(**rec))

        return Article(
            id=doc['_id'],
            inputs=ArticleInputs(**doc['inputs']),
            status=ArticleStatus(doc['status']),
            created_at=doc['created_at'],
            updated_at=doc['updated_at'],
            user_id=doc.get('user_id'),
            job_id=doc.get('job_id'),
            content=doc.get('content'),
            started_at=doc.get('started_at'),
            source=source,
            edit_history=edit_history,
        )

    # ── write operations ─────────────────────────────────────

    def save(self, article: Article) -> bool:
        """Save entire Article (upsert)."""
        try:
            doc = {
                'inputs': asdict(article.inputs),
                'status': article.status.value,
                'updated_at': article.updated_at,
                'user_id': article.user_id,
                'job_id': article.job_id,
                'content': article.content,
                'started_at': article.started_at,
                'source': asdict(article.source) if article.source else None,
                'edit_history': [asdict(r) for r in article.edit_history],
            }

            self.collection.update_one(
                {'_id': article.id},
                {
                    '$set': doc,
                    '$setOnInsert': {'created_at': article.created_at, '_id': article.id},
                },
                upsert=True,
            )

            logger.info("Article saved", extra={"articleId": article.id})
            return True
        except PyMongoError as e:
            logger.error("Failed to save article", extra={"articleId": article.id, "error": str(e)})
            return False

    def update_status(self, article_id: str, status: ArticleStatus) -> bool:
        """Update article status."""
        try:
            result = self.collection.update_one(
                {'_id': article_id},
                {'$set': {'status': status.value, 'updated_at': datetime.now(timezone.utc)}},
            )

            if result.matched_count == 0:
                logger.warning("Article not found for status update", extra={"articleId": article_id})
                return False

            logger.debug("Article status updated", extra={"articleId": article_id, "status": status.value})
            return True
        except PyMongoError as e:
            logger.error("Failed to update article status", extra={"articleId": article_id, "error": str(e)})
            return False

    def delete(self, article_id: str) -> bool:
        """Soft delete article by setting status to DELETED."""
        try:
            result = self.collection.update_one(
                {'_id': article_id},
                {'$set': {'status': ArticleStatus.DELETED.value, 'updated_at': datetime.now(timezone.utc)}},
            )

            if result.matched_count == 0:
                logger.warning("Article not found for deletion", extra={"articleId": article_id})
                return False

            logger.info("Article soft deleted", extra={"articleId": article_id})
            return True
        except PyMongoError as e:
            logger.error("Failed to delete article", extra={"articleId": article_id, "error": str(e)})
            return False

    # ── read operations ──────────────────────────────────────

    def get_by_id(self, article_id: str) -> Article | None:
        """Retrieve article by ID."""
        try:
            doc = self.collection.find_one({'_id': article_id})
            if doc:
                return self._to_domain(doc)
            return None
        except PyMongoError as e:
            logger.error("Failed to retrieve article", extra={"articleId": article_id, "error": str(e)})
            return None

    def find_many(
        self,
        skip: int = 0,
        limit: int = 20,
        status: ArticleStatus | None = None,
        language: str | None = None,
        level: str | None = None,
        user_id: str | None = None,
        exclude_deleted: bool = True,
    ) -> Articles:
        """List articles with filtering, sorting, and pagination."""
        try:
            query: dict = {}
            if status:
                query['status'] = status.value
            elif exclude_deleted:
                query['status'] = {'$ne': ArticleStatus.DELETED.value}
            if language:
                query['inputs.language'] = language
            if level:
                query['inputs.level'] = level
            if user_id:
                query['user_id'] = user_id

            total_count = self.collection.count_documents(query)
            docs = (
                self.collection.find(query)
                .sort('created_at', -1)
                .skip(skip)
                .limit(limit)
            )

            articles = [self._to_domain(doc) for doc in docs]
            logger.info("Listed articles", extra={"count": len(articles), "total": total_count})
            return Articles(items=articles, total=total_count)
        except PyMongoError as e:
            logger.error("Failed to list articles", extra={"error": str(e)})
            return Articles(items=[], total=0)

    def find_duplicate(
        self,
        inputs: ArticleInputs,
        user_id: str | None = None,
        hours: int = 24,
    ) -> Article | None:
        """Find duplicate article by inputs within specified hours."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            query = {
                'inputs': asdict(inputs),
                'created_at': {'$gte': cutoff},
                'user_id': user_id,
            }

            doc = self.collection.find_one(query, sort=[('created_at', -1)])
            if doc:
                logger.debug("Found duplicate article", extra={"articleId": doc['_id']})
                return self._to_domain(doc)
            return None
        except PyMongoError as e:
            logger.error("Failed to find duplicate article", extra={"error": str(e)})
            return None

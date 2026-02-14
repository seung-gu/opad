"""MongoDB implementation of ArticleRepository."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from logging import getLogger

from pymongo.errors import PyMongoError

from adapter.mongodb import COLLECTION_NAME
from domain.model.article import Article, ArticleInputs, ArticleStatus

logger = getLogger(__name__)


class MongoArticleRepository:
    def __init__(self, db):
        self.collection = db[COLLECTION_NAME]

    # ── helpers ──────────────────────────────────────────────

    def _to_domain(self, doc: dict) -> Article:
        """Convert MongoDB document to Article domain model."""
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
        )

    # ── write operations ─────────────────────────────────────

    def save_metadata(
        self,
        article_id: str,
        inputs: ArticleInputs,
        status: ArticleStatus = ArticleStatus.RUNNING,
        created_at: datetime | None = None,
        user_id: str | None = None,
        job_id: str | None = None,
    ) -> bool:
        """Save article metadata to MongoDB (without content)."""
        try:
            if created_at is None:
                created_at = datetime.now(timezone.utc)

            article_doc = {
                'inputs': asdict(inputs),
                'status': status.value,
                'updated_at': datetime.now(timezone.utc),
                'user_id': user_id,
                'job_id': job_id,
            }

            self.collection.update_one(
                {'_id': article_id},
                {
                    '$set': article_doc,
                    '$setOnInsert': {'created_at': created_at, '_id': article_id},
                },
                upsert=True,
            )

            logger.info("Article metadata saved", extra={"articleId": article_id, "jobId": job_id})
            return True
        except PyMongoError as e:
            logger.error("Failed to save article metadata", extra={"articleId": article_id, "error": str(e)})
            return False

    def save_content(
        self,
        article_id: str,
        content: str,
        started_at: datetime | None = None,
    ) -> bool:
        """Save generated article content and mark as completed."""
        try:
            update_data = {
                'content': content,
                'status': ArticleStatus.COMPLETED.value,
                'updated_at': datetime.now(timezone.utc),
            }
            if started_at:
                update_data['started_at'] = started_at

            result = self.collection.update_one(
                {'_id': article_id},
                {'$set': update_data},
            )

            if result.matched_count == 0:
                logger.error("Article not found, cannot save content", extra={"articleId": article_id})
                return False

            logger.info("Article content saved", extra={"articleId": article_id})
            return True
        except PyMongoError as e:
            logger.error("Failed to save article content", extra={"articleId": article_id, "error": str(e)})
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
    ) -> tuple[list[Article], int]:
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
            return articles, total_count
        except PyMongoError as e:
            logger.error("Failed to list articles", extra={"error": str(e)})
            return [], 0

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

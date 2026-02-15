"""MongoDB implementation of TokenUsageRepository."""

import uuid
from datetime import datetime, timedelta, timezone
from pymongo.database import Database
from pymongo.errors import PyMongoError
from logging import getLogger

from adapter.mongodb import TOKEN_USAGE_COLLECTION_NAME
from domain.model.token_usage import TokenUsage, TokenUsageSummary, OperationUsage, DailyUsage

logger = getLogger(__name__)


class MongoTokenUsageRepository:
    def __init__(self, db: Database):
        self.collection = db[TOKEN_USAGE_COLLECTION_NAME]

    def ensure_indexes(self) -> bool:
        """Create indexes for token_usage collection."""
        from adapter.mongodb.indexes import create_index_safe

        try:
            create_index_safe(self.collection, [('user_id', 1), ('created_at', -1)], 'idx_token_user_created')
            create_index_safe(self.collection, [('article_id', 1)], 'idx_token_article_id', sparse=True)
            create_index_safe(self.collection, [('created_at', -1)], 'idx_token_created_at')
            create_index_safe(self.collection, [('operation', 1), ('created_at', -1)], 'idx_token_operation_created')
            return True
        except Exception as e:
            logger.error("Failed to create token_usage indexes", extra={"error": str(e)})
            return False

    def _to_domain(self, doc: dict) -> TokenUsage:
        """Convert MongoDB document to TokenUsage domain model."""
        return TokenUsage(
            id=doc['_id'],
            user_id=doc['user_id'],
            operation=doc['operation'],
            model=doc['model'],
            prompt_tokens=doc['prompt_tokens'],
            completion_tokens=doc['completion_tokens'],
            total_tokens=doc['total_tokens'],
            estimated_cost=doc['estimated_cost'],
            article_id=doc.get('article_id'),
            created_at=doc['created_at'],
            metadata=doc.get('metadata', {}),
        )

    def save(
        self,
        user_id: str,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
        article_id: str | None = None,
        metadata: dict | None = None,
    ) -> str | None:
        """Save token usage record to MongoDB.

        Records token usage for cost tracking and analytics.

        Args:
            user_id: User ID who incurred the usage
            operation: Operation type ("dictionary_search" | "article_generation")
            model: Model name used (e.g., "gpt-4", "claude-3-opus")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            estimated_cost: Estimated cost in USD
            article_id: Optional article ID if usage is associated with an article
            metadata: Optional additional metadata (e.g., query, language)

        Returns:
            Inserted document ID if successful, None otherwise
        """
        # Validate inputs
        if not user_id or not user_id.strip():
            logger.warning("Invalid user_id for token usage: empty or whitespace")
            return None
        if prompt_tokens < 0 or completion_tokens < 0:
            logger.warning(
                "Invalid token counts for token usage",
                extra={"promptTokens": prompt_tokens, "completionTokens": completion_tokens}
            )
            return None

        try:
            now = datetime.now(timezone.utc)
            usage_doc = {
                '_id': str(uuid.uuid4()),
                'user_id': user_id,
                'operation': operation,
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'estimated_cost': estimated_cost,
                'article_id': article_id,
                'metadata': metadata or {},
                'created_at': now
            }

            self.collection.insert_one(usage_doc)
            usage_id = usage_doc['_id']

            logger.info(
                "Token usage saved",
                extra={
                    "usageId": usage_id,
                    "userId": user_id,
                    "operation": operation,
                    "totalTokens": prompt_tokens + completion_tokens,
                    "estimatedCost": estimated_cost
                }
            )
            return usage_id
        except PyMongoError as e:
            logger.error(
                "Failed to save token usage",
                extra={"userId": user_id, "operation": operation, "error": str(e)}
            )
            return None

    def get_user_summary(self, user_id: str, days: int = 30) -> TokenUsageSummary:
        """Get token usage summary for a user.

        Aggregates token usage data for the specified user within the time window.

        Args:
            user_id: User ID to get summary for
            days: Number of days to look back (default: 30, clamped to [1, 365])

        Returns:
            TokenUsageSummary with aggregated usage data.
        """
        # Clamp days to valid range [1, 365]
        if days < 1 or days > 365:
            logger.warning(
                f"Invalid days value {days} for token summary, clamping to [1, 365]",
                extra={"userId": user_id, "requestedDays": days}
            )
            days = max(1, min(days, 365))

        try:
            # Calculate cutoff date
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            # Aggregation for totals and by operation
            operation_pipeline = [
                {
                    '$match': {
                        'user_id': user_id,
                        'created_at': {'$gte': cutoff}
                    }
                },
                {
                    '$group': {
                        '_id': '$operation',
                        'tokens': {'$sum': '$total_tokens'},
                        'cost': {'$sum': '$estimated_cost'},
                        'count': {'$sum': 1}
                    }
                }
            ]

            by_operation = {}
            total_tokens = 0
            total_cost = 0.0

            for doc in self.collection.aggregate(operation_pipeline):
                op = doc['_id']
                tokens = doc['tokens']
                cost = doc['cost']
                count = doc['count']

                by_operation[op] = {
                    'tokens': tokens,
                    'cost': round(cost, 6),
                    'count': count
                }
                total_tokens += tokens
                total_cost += cost

            # Aggregation for daily usage
            daily_pipeline = [
                {
                    '$match': {
                        'user_id': user_id,
                        'created_at': {'$gte': cutoff}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$created_at'
                            }
                        },
                        'tokens': {'$sum': '$total_tokens'},
                        'cost': {'$sum': '$estimated_cost'}
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]

            daily_usages = []
            for doc in self.collection.aggregate(daily_pipeline):
                daily_usages.append({
                    'date': doc['_id'],
                    'tokens': doc['tokens'],
                    'cost': round(doc['cost'], 6)
                })

            logger.info(
                "Token usage summary retrieved",
                extra={
                    "userId": user_id,
                    "days": days,
                    "totalTokens": total_tokens,
                    "totalCost": round(total_cost, 6)
                }
            )

            return TokenUsageSummary(
                total_tokens=total_tokens,
                total_cost=round(total_cost, 6),
                by_operation={k: OperationUsage(**v) for k, v in by_operation.items()},
                daily_usage=[DailyUsage(**daily_usage) for daily_usage in daily_usages]
            )
        except PyMongoError as e:
            logger.error(
                "Failed to get token usage summary",
                extra={"userId": user_id, "error": str(e)}
            )
            return TokenUsageSummary(
                total_tokens=0,
                total_cost=0.0,
                by_operation={},
                daily_usage=[]
            )

    def get_by_article(self, article_id: str) -> list[TokenUsage]:
        """Get all token usage records for an article.

        Retrieves all token usage records associated with a specific article,
        sorted by created_at ascending (oldest first).

        Args:
            article_id: Article ID to get usage for

        Returns:
            List of TokenUsage domain objects sorted by created_at ascending.
        """
        # Validate article_id
        if not article_id or not article_id.strip():
            logger.warning("Invalid article_id for token usage query: empty or whitespace")
            return []

        try:
            result = []
            for doc in self.collection.find({'article_id': article_id}).sort('created_at', 1):
                result.append(self._to_domain(doc))

            logger.info(
                "Article token usage retrieved",
                extra={"articleId": article_id, "recordCount": len(result)}
            )
            return result
        except PyMongoError as e:
            logger.error(
                "Failed to get article token usage",
                extra={"articleId": article_id, "error": str(e)}
            )
            return []

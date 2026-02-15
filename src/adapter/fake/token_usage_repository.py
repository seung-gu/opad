"""In-memory implementation of TokenUsageRepository for testing."""

import uuid
from datetime import datetime, timedelta, timezone

from domain.model.token_usage import DailyUsage, OperationUsage, TokenUsage, TokenUsageSummary


class FakeTokenUsageRepository:
    def __init__(self):
        self.store: dict[str, TokenUsage] = {}

    # ── write operations ─────────────────────────────────────

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
        if not user_id or not user_id.strip():
            return None
        if prompt_tokens < 0 or completion_tokens < 0:
            return None

        record_id = str(uuid.uuid4())
        record = TokenUsage(
            id=record_id,
            user_id=user_id,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=estimated_cost,
            created_at=datetime.now(timezone.utc),
            article_id=article_id,
            metadata=metadata or {},
        )
        self.store[record_id] = record
        return record_id

    # ── read operations ──────────────────────────────────────

    def get_user_summary(self, user_id: str, days: int = 30) -> TokenUsageSummary:
        days = max(1, min(days, 365))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        by_operation: dict[str, OperationUsage] = {}
        daily_buckets: dict[str, dict] = {}
        total_tokens = 0
        total_cost = 0.0

        for record in self.store.values():
            if record.user_id != user_id or record.created_at < cutoff:
                continue

            total_tokens += record.total_tokens
            total_cost += record.estimated_cost

            op = record.operation
            if op in by_operation:
                existing = by_operation[op]
                by_operation[op] = OperationUsage(
                    tokens=existing.tokens + record.total_tokens,
                    cost=round(existing.cost + record.estimated_cost, 6),
                    count=existing.count + 1,
                )
            else:
                by_operation[op] = OperationUsage(
                    tokens=record.total_tokens,
                    cost=round(record.estimated_cost, 6),
                    count=1,
                )

            date_key = record.created_at.strftime('%Y-%m-%d')
            if date_key in daily_buckets:
                daily_buckets[date_key]['tokens'] += record.total_tokens
                daily_buckets[date_key]['cost'] += record.estimated_cost
            else:
                daily_buckets[date_key] = {
                    'tokens': record.total_tokens,
                    'cost': record.estimated_cost,
                }

        daily_usage = [
            DailyUsage(date=k, tokens=v['tokens'], cost=round(v['cost'], 6))
            for k, v in sorted(daily_buckets.items())
        ]

        return TokenUsageSummary(
            total_tokens=total_tokens,
            total_cost=round(total_cost, 6),
            by_operation=by_operation,
            daily_usage=daily_usage,
        )

    def get_by_article(self, article_id: str) -> list[TokenUsage]:
        if not article_id or not article_id.strip():
            return []

        return sorted(
            [r for r in self.store.values() if r.article_id == article_id],
            key=lambda r: r.created_at,
        )

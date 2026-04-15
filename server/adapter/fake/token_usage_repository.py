"""In-memory implementation of TokenUsageRepository for testing."""

from datetime import datetime, timedelta, timezone

from domain.model.token_usage import TokenUsage


class FakeTokenUsageRepository:
    def __init__(self):
        self.store: dict[str, dict] = {}

    # ── write operations ─────────────────────────────────────

    def save(self, usage: TokenUsage) -> str | None:
        if not usage.user_id or not usage.user_id.strip():
            return None
        if usage.prompt_tokens < 0 or usage.completion_tokens < 0:
            return None

        self.store[usage.id] = {
            'id': usage.id,
            'user_id': usage.user_id,
            'operation': usage.operation,
            'model': usage.model,
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens,
            'estimated_cost': usage.estimated_cost,
            'created_at': usage.created_at,
            'article_id': usage.article_id,
            'metadata': usage.metadata or {},
        }
        return usage.id

    # ── read operations ──────────────────────────────────────

    def get_user_summary(self, user_id: str, days: int = 30) -> dict:
        days = max(1, min(days, 365))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        by_operation: dict[str, dict] = {}
        daily_buckets: dict[str, dict] = {}
        total_tokens = 0
        total_cost = 0.0

        for record in self.store.values():
            if record['user_id'] != user_id or record['created_at'] < cutoff:
                continue

            total_tokens += record['total_tokens']
            total_cost += record['estimated_cost']

            op = record['operation']
            if op in by_operation:
                existing = by_operation[op]
                existing['tokens'] += record['total_tokens']
                existing['cost'] = round(existing['cost'] + record['estimated_cost'], 6)
                existing['count'] += 1
            else:
                by_operation[op] = {
                    'tokens': record['total_tokens'],
                    'cost': round(record['estimated_cost'], 6),
                    'count': 1,
                }

            date_key = record['created_at'].strftime('%Y-%m-%d')
            if date_key in daily_buckets:
                daily_buckets[date_key]['tokens'] += record['total_tokens']
                daily_buckets[date_key]['cost'] += record['estimated_cost']
            else:
                daily_buckets[date_key] = {
                    'tokens': record['total_tokens'],
                    'cost': record['estimated_cost'],
                }

        daily_usage = [
            {'date': k, 'tokens': v['tokens'], 'cost': round(v['cost'], 6)}
            for k, v in sorted(daily_buckets.items())
        ]

        return {
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 6),
            'by_operation': by_operation,
            'daily_usage': daily_usage,
        }

    def get_by_article(self, article_id: str) -> list[dict]:
        if not article_id or not article_id.strip():
            return []

        return sorted(
            [r for r in self.store.values() if r['article_id'] == article_id],
            key=lambda r: r['created_at'],
        )

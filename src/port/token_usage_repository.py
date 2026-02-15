from typing import Protocol

from domain.model.token_usage import TokenUsage, TokenUsageSummary


class TokenUsageRepository(Protocol):
    """Protocol defining the interface for token usage data access."""

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
        """Save a token usage record. Return record ID or None on failure."""
        ...

    def get_user_summary(self, user_id: str, days: int = 30) -> TokenUsageSummary:
        """Get aggregated token usage summary for a user within the time window."""
        ...

    def get_by_article(self, article_id: str) -> list[TokenUsage]:
        """Get all token usage records for an article, sorted by created_at ascending."""
        ...

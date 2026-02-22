from typing import Any, Protocol

from domain.model.token_usage import TokenUsage


class TokenUsageRepository(Protocol):
    """Protocol defining the interface for token usage data access."""

    def save(self, usage: TokenUsage) -> str | None:
        """Save a token usage record.

        Uses the id and created_at from the domain object.
        Returns record ID or None on failure.
        """
        ...

    def get_user_summary(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """Get aggregated token usage summary for a user within the time window."""
        ...

    def get_by_article(self, article_id: str) -> list[dict[str, Any]]:
        """Get all token usage records for an article, sorted by created_at ascending."""
        ...

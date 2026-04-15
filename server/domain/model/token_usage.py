"""Domain models for LLM call results and token usage tracking."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class LLMCallResult:
    """Result from a single LLM API call (Value Object).

    Attributes:
        model: The model name used for the API call.
        prompt_tokens: Number of tokens in the prompt/input.
        completion_tokens: Number of tokens in the completion/output.
        total_tokens: Total tokens used (prompt + completion).
        estimated_cost: Estimated cost in USD based on model pricing.
        provider: Optional provider name (e.g., "openai", "anthropic", "google").
    """
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    provider: str | None = field(default=None)


@dataclass
class TokenUsage:
    """A single token usage record (Entity).

    Tracks who used how many tokens for which operation.
    Created by service layer, persisted by adapter.
    """
    id: str
    user_id: str
    operation: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    created_at: datetime
    article_id: str | None = None
    metadata: dict | None = None

    @classmethod
    def from_llm_result(
        cls,
        stats: 'LLMCallResult',
        user_id: str,
        operation: str,
        article_id: str | None = None,
        metadata: dict | None = None,
    ) -> 'TokenUsage':
        """Create a TokenUsage record from an LLM call result."""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            operation=operation,
            model=stats.model,
            prompt_tokens=stats.prompt_tokens,
            completion_tokens=stats.completion_tokens,
            total_tokens=stats.total_tokens,
            estimated_cost=stats.estimated_cost,
            created_at=datetime.now(timezone.utc),
            article_id=article_id,
            metadata=metadata,
        )

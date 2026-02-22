"""Domain models for LLM call results and token usage tracking."""

from dataclasses import dataclass, field
from datetime import datetime


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

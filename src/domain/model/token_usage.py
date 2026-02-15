"""Domain models for token usage tracking."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenUsage:
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
    metadata: dict = field(default_factory=dict)


@dataclass
class OperationUsage:
    tokens: int
    cost: float
    count: int


@dataclass
class DailyUsage:
    date: str
    tokens: int
    cost: float


@dataclass
class TokenUsageSummary:
    total_tokens: int
    total_cost: float
    by_operation: dict[str, OperationUsage] = field(default_factory=dict)
    daily_usage: list[DailyUsage] = field(default_factory=list)

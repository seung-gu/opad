"""LLM port — outbound interface for large language model calls."""

from typing import Protocol

from domain.model.token_usage import LLMCallResult


class LLMError(Exception):
    """Base exception for LLM port errors."""


class LLMTimeoutError(LLMError):
    """LLM request timed out."""


class LLMRateLimitError(LLMError):
    """LLM provider rate limit exceeded."""


class LLMAuthError(LLMError):
    """LLM provider authentication failed."""


class LLMPort(Protocol):
    """Port for making LLM API calls with token usage tracking."""

    async def call(
        self,
        messages: list[dict[str, str]],
        model: str = "openai/gpt-4.1-mini",
        timeout: float = 30.0,
        **kwargs,
    ) -> tuple[str, LLMCallResult]: ...

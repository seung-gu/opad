"""In-memory implementation of LLMPort for testing."""

from domain.model.token_usage import LLMCallResult


class FakeLLMAdapter:
    """Fake LLM adapter that returns preconfigured responses."""

    def __init__(
        self,
        response: str = "{}",
        stats: LLMCallResult | None = None,
    ):
        self.response = response
        self._stats = stats
        self.calls: list[dict] = []

    async def call(
        self,
        messages: list[dict[str, str]],
        model: str = "openai/gpt-4.1-mini",
        timeout: float = 30.0,
        **kwargs,
    ) -> tuple[str, LLMCallResult]:
        self.calls.append({
            "messages": messages,
            "model": model,
            "timeout": timeout,
            **kwargs,
        })
        stats = self._stats or LLMCallResult(
            model=model,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost=0.0001,
        )
        return self.response, stats

    def estimate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int,
    ) -> float:
        """Fake cost estimation — always returns 0.0."""
        return 0.0

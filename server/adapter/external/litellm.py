"""LiteLLM adapter — implements LLMPort using LiteLLM for provider-agnostic LLM calls."""

import logging

import litellm
from litellm import acompletion, completion_cost

from domain.model.token_usage import LLMCallResult
from port.llm import LLMAuthError, LLMError, LLMRateLimitError, LLMTimeoutError

# Suppress LiteLLM's verbose logging (proxy server warnings, etc.)
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


def _extract_provider_from_model(model: str) -> str | None:
    """Extract provider name from model string.

    Args:
        model: Model string (e.g., "gpt-4.1-mini", "anthropic/claude-4.5-sonnet")

    Returns:
        Provider name or None if not specified in model string.
    """
    if "/" in model:
        return model.split("/")[0]
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    return None


class LiteLLMAdapter:
    """Adapter that implements LLMPort using LiteLLM for provider-agnostic LLM calls."""

    async def call(
        self,
        messages: list[dict[str, str]],
        model: str = "openai/gpt-4.1-mini",
        timeout: float = 30.0,
        **kwargs,
    ) -> tuple[str, LLMCallResult]:
        """Call LLM API with token usage tracking.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: LiteLLM model identifier.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to litellm.acompletion().

        Returns:
            Tuple of (content, stats).

        Raises:
            ValueError: If messages list is empty.
            litellm.Timeout: If request times out.
            litellm.APIError: If the LLM API returns an error.
            RuntimeError: If no content is returned from the API.
        """
        if not messages:
            raise ValueError("messages list cannot be empty")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                timeout=timeout,
                **kwargs,
            )
        except litellm.Timeout as e:
            raise LLMTimeoutError(str(e)) from e
        except litellm.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except litellm.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except litellm.APIError as e:
            raise LLMError(str(e)) from e

        content = ""
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message and message.content:
                content = message.content.strip()

        if not content:
            logger.error("No content in LLM response", extra={
                "model": model,
                "response_id": getattr(response, "id", None),
            })
            raise RuntimeError("No content returned from LLM")

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        try:
            estimated_cost = completion_cost(completion_response=response)
        except Exception as e:
            logger.debug("Could not calculate cost with LiteLLM", extra={
                "model": model, "error": str(e),
            })
            estimated_cost = 0.0

        provider = _extract_provider_from_model(model)

        stats = LLMCallResult(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            provider=provider,
        )

        logger.debug("LLM API call completed", extra={
            "model": model, "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
        })

        return content, stats

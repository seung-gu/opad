"""Common utilities for LLM API calls using LiteLLM for provider-agnostic support."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import litellm
from litellm import acompletion, completion_cost

# Suppress LiteLLM's verbose logging (proxy server warnings, etc.)
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


@dataclass
class TokenUsageStats:
    """Statistics for token usage from an LLM API call.

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize TokenUsageStats to a dictionary.

        Returns:
            Dictionary representation of the token usage statistics.
        """
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.estimated_cost,
            "provider": self.provider,
        }


def accumulate_stats(
    *stats_list: TokenUsageStats | None,
) -> TokenUsageStats | None:
    """Accumulate multiple TokenUsageStats into one.

    Args:
        *stats_list: Variable number of TokenUsageStats (None values are ignored).

    Returns:
        Combined stats, single stats if only one valid, or None if all None.
    """
    valid = [s for s in stats_list if s is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    return TokenUsageStats(
        model=valid[0].model,
        prompt_tokens=sum(s.prompt_tokens for s in valid),
        completion_tokens=sum(s.completion_tokens for s in valid),
        total_tokens=sum(s.total_tokens for s in valid),
        estimated_cost=sum(s.estimated_cost for s in valid),
        provider=valid[0].provider,
    )


def parse_json_from_content(content: str) -> dict | None:
    """Parse JSON from LLM response content.

    Handles various formats:
    - Plain JSON: {"key": "value"}
    - JSON in markdown code blocks: ```json {...} ```
    - JSON with surrounding text

    Args:
        content: Raw content string from LLM

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    try:
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            json_match = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_match = content.split("```")[1].split("```")[0]
        elif "{" in content:
            # Extract JSON from text that might have surrounding content
            start = content.index("{")
            end = content.rindex("}") + 1
            json_match = content[start:end]
        else:
            json_match = content

        return json.loads(json_match.strip())
    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.debug("Failed to parse JSON from content", extra={
            "error": str(e),
            "content_preview": content[:200]
        })
        return None


def _extract_provider_from_model(model: str) -> str | None:
    """Extract provider name from model string.

    Args:
        model: Model string (e.g., "gpt-4.1-mini", "anthropic/claude-4.5-sonnet")

    Returns:
        Provider name or None if not specified in model string.
    """
    if "/" in model:
        return model.split("/")[0]
    # OpenAI models don't have a prefix
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    return None


async def call_llm_with_tracking(
    messages: list[dict[str, str]],
    model: str = "gpt-4.1-mini",
    timeout: float = 30.0,
    **kwargs
) -> tuple[str, TokenUsageStats]:
    """Call LLM API with token usage tracking using LiteLLM.

    This is a provider-agnostic function that supports multiple LLM providers
    through LiteLLM. It automatically calculates costs using LiteLLM's
    built-in pricing database.

    Model format examples:
        - OpenAI: "gpt-4.1-mini", "gpt-4.1"
        - Anthropic: "anthropic/claude-4.5-sonnet"
        - Google: "gemini/gemini-2.0-flash"

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
            Example: [{"role": "user", "content": "Hello"}]
        model: LiteLLM model identifier (default: gpt-4.1-mini).
        timeout: Request timeout in seconds (default: 30.0).
        **kwargs: Additional arguments passed to litellm.acompletion()
            (e.g., max_tokens, temperature, top_p).

    Returns:
        Tuple of (content, stats):
            - content: The response content string from the model.
            - stats: TokenUsageStats with token counts and estimated cost.

    Raises:
        ValueError: If messages list is empty.
        litellm.AuthenticationError: If API key is invalid.
        litellm.RateLimitError: If rate limit is exceeded.
        litellm.Timeout: If request times out.
        litellm.APIError: If the LLM API returns an error.
        litellm.ServiceUnavailableError: If the service is unavailable.
        RuntimeError: If no content is returned from the API.
    """
    if not messages:
        raise ValueError("messages list cannot be empty")

    response = await acompletion(
        model=model,
        messages=messages,
        timeout=timeout,
        **kwargs
    )

    # Extract content from response
    content = ""
    if response.choices and len(response.choices) > 0:
        message = response.choices[0].message
        if message and message.content:
            content = message.content.strip()

    if not content:
        logger.error("No content in LLM response", extra={
            "model": model,
            "response_id": getattr(response, "id", None)
        })
        raise RuntimeError("No content returned from LLM")

    # Extract usage statistics
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens = usage.total_tokens if usage else 0

    # Calculate estimated cost using LiteLLM's built-in pricing
    try:
        estimated_cost = completion_cost(completion_response=response)
    except Exception as e:
        logger.debug("Could not calculate cost with LiteLLM", extra={
            "model": model,
            "error": str(e)
        })
        estimated_cost = 0.0

    # Extract provider from model string
    provider = _extract_provider_from_model(model)

    stats = TokenUsageStats(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        provider=provider
    )

    logger.debug("LLM API call completed with tracking", extra={
        "model": model,
        "provider": provider,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost
    })

    return content, stats


def get_llm_error_response(e: Exception) -> tuple[int, str]:
    """Get HTTP status code and detail message for LLM-related exceptions.

    Args:
        e: Exception to handle

    Returns:
        Tuple of (status_code, detail_message)
    """
    if isinstance(e, litellm.AuthenticationError):
        return (401, "LLM provider authentication failed")
    elif isinstance(e, litellm.RateLimitError):
        return (429, "LLM provider rate limit exceeded")
    elif isinstance(e, litellm.Timeout):
        return (504, "LLM provider timeout")
    elif isinstance(e, litellm.ServiceUnavailableError):
        return (503, "LLM provider service unavailable")
    elif isinstance(e, litellm.APIError):
        return (502, "LLM provider API error")
    elif isinstance(e, ValueError):
        return (400, f"Invalid request: {str(e)}")
    elif isinstance(e, RuntimeError):
        return (500, f"LLM provider error: {str(e)}")
    else:
        return (500, "Internal server error")

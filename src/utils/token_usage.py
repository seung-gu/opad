"""Token usage utilities for cost calculation.

Provides LiteLLM-based cost estimation for LLM API calls.
Used by token_usage_service for CrewAI agents that bypass our LLMPort.
"""

import logging

logger = logging.getLogger(__name__)


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost using LiteLLM's pricing data.

    Note: LiteLLM pricing may become outdated. Costs are estimates only.

    Args:
        model: Model name (e.g., 'gpt-4.1', 'gpt-4.1-mini')
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Estimated cost in USD, or 0.0 if pricing unavailable
    """
    try:
        import litellm
        # cost_per_token returns TOTAL cost for given token counts, not per-token rate
        prompt_cost, completion_cost = litellm.cost_per_token(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        return prompt_cost + completion_cost
    except (KeyError, ValueError, AttributeError):
        # Model not in LiteLLM pricing database or invalid response
        return 0.0
    except Exception as e:
        # Unexpected error - log at debug level for troubleshooting
        logger.debug(f"Unexpected error calculating cost for {model}: {e}")
        return 0.0

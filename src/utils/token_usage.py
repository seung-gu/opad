"""Token usage utilities for cost calculation and tracking.

This module provides utilities for:
- Calculating LLM costs using LiteLLM's pricing database
- Saving CrewAI agent token usage to MongoDB
"""

import logging
from typing import TYPE_CHECKING

from utils.mongodb import save_token_usage

if TYPE_CHECKING:
    from crew.main import CrewResult

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


def save_crew_token_usage(
    result: "CrewResult",
    user_id: str,
    article_id: str | None,
    job_id: str
) -> None:
    """Save token usage for each CrewAI agent to MongoDB.

    Uses CrewAI's built-in token tracking (agent.llm.get_token_usage_summary())
    to get per-agent, per-model usage metrics. Cost is calculated using
    LiteLLM's pricing database.

    Args:
        result: CrewResult containing crew_instance with agents
        user_id: User ID who initiated the generation
        article_id: Article ID being generated
        job_id: Job ID for metadata
    """
    try:
        agent_usage = result.get_agent_usage()
        total_saved = 0

        # Debug: Log what get_agent_usage returns
        logger.info(
            "Agent usage retrieved",
            extra={
                "jobId": job_id,
                "agentCount": len(agent_usage),
                "usageData": [
                    {"role": u.get('agent_role'), "model": u.get('model'), "tokens": u.get('total_tokens')}
                    for u in agent_usage
                ]
            }
        )

        for usage in agent_usage:
            # Skip if no tokens were used
            if usage['total_tokens'] == 0:
                continue

            # Calculate cost using LiteLLM pricing
            estimated_cost = calculate_cost(
                model=usage['model'],
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens']
            )

            # Use agent_name if it's a non-empty string, otherwise fallback to agent_role
            agent_name = usage.get('agent_name')
            display_name = agent_name if isinstance(agent_name, str) and agent_name else usage['agent_role']

            save_token_usage(
                user_id=user_id,
                operation="article_generation",
                model=usage['model'],
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens'],
                estimated_cost=estimated_cost,
                article_id=article_id,
                metadata={"job_id": job_id, "agent_name": display_name}
            )
            total_saved += 1

        logger.info(
            "Token usage saved for article generation",
            extra={
                "jobId": job_id,
                "articleId": article_id,
                "agentCount": total_saved
            }
        )
    except Exception as e:
        # Non-fatal: don't fail the job if token tracking fails
        logger.warning(
            "Failed to save token usage (non-fatal)",
            extra={"jobId": job_id, "error": str(e), "errorType": type(e).__name__}
        )

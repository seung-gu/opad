"""Token usage service — creates TokenUsage domain objects and saves via repository."""

import logging
import uuid
from datetime import datetime, timezone

from domain.model.token_usage import LLMCallResult, TokenUsage
from port.token_usage_repository import TokenUsageRepository
from port.llm import LLMPort

logger = logging.getLogger(__name__)


def track_llm_usage(
    repo: TokenUsageRepository,
    stats: LLMCallResult | None,
    user_id: str,
    operation: str,
    article_id: str | None = None,
    metadata: dict | None = None,
) -> str | None:
    """Track token usage from a single LLM call.

    Creates a TokenUsage domain object from LLMCallResult and saves it.

    Returns:
        Saved record ID, or None if stats is None or save failed.
    """
    if not stats:
        return None

    usage = TokenUsage(
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
    return repo.save(usage)


def track_agent_usage(
    repo: TokenUsageRepository,
    agent_usage: list[dict],
    user_id: str,
    article_id: str | None,
    job_id: str,
    llm: LLMPort | None = None,
) -> None:
    """Track token usage for each agent (framework-agnostic).

    Accepts a list of dicts with agent_role, agent_name, model, prompt_tokens,
    completion_tokens, total_tokens.
    """
    try:
        total_saved = 0

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

        for agent in agent_usage:
            if agent.get('total_tokens', 0) == 0:
                continue

            agent_name = agent.get('agent_name')
            display_name = agent_name if isinstance(agent_name, str) and agent_name else agent.get('agent_role', 'unknown')

            stats = LLMCallResult(
                model=agent.get('model', 'unknown'),
                prompt_tokens=agent.get('prompt_tokens', 0),
                completion_tokens=agent.get('completion_tokens', 0),
                total_tokens=agent.get('total_tokens', 0),
                estimated_cost=llm.estimate_cost(
                    model=agent.get('model', 'unknown'),
                    prompt_tokens=agent.get('prompt_tokens', 0),
                    completion_tokens=agent.get('completion_tokens', 0),
                ) if llm else 0.0,
            )
            result_id = track_llm_usage(
                repo, stats, user_id,
                operation="article_generation",
                article_id=article_id,
                metadata={"job_id": job_id, "agent_name": display_name},
            )
            if result_id:
                total_saved += 1

        logger.info(
            "Token usage saved for article generation",
            extra={
                "jobId": job_id,
                "articleId": article_id,
                "agentCount": total_saved,
            }
        )
    except Exception as e:
        logger.warning(
            "Failed to save token usage (non-fatal)",
            extra={"jobId": job_id, "error": str(e), "errorType": type(e).__name__},
        )

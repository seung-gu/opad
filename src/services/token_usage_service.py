"""Token usage service — creates TokenUsage domain objects and saves via repository."""

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from domain.model.token_usage import LLMCallResult, TokenUsage
from port.token_usage_repository import TokenUsageRepository
from utils.token_usage import calculate_cost

if TYPE_CHECKING:
    from crew.main import CrewResult

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


def track_crew_usage(
    repo: TokenUsageRepository,
    result: "CrewResult",
    user_id: str,
    article_id: str | None,
    job_id: str,
) -> None:
    """Track token usage for each CrewAI agent.

    Converts each agent's usage to LLMCallResult, then delegates to track_llm_usage.
    """
    try:
        agent_usage = result.get_agent_usage()
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
            if agent['total_tokens'] == 0:
                continue

            agent_name = agent.get('agent_name')
            display_name = agent_name if isinstance(agent_name, str) and agent_name else agent['agent_role']

            stats = LLMCallResult(
                model=agent['model'],
                prompt_tokens=agent['prompt_tokens'],
                completion_tokens=agent['completion_tokens'],
                total_tokens=agent['total_tokens'],
                estimated_cost=calculate_cost(
                    model=agent['model'],
                    prompt_tokens=agent['prompt_tokens'],
                    completion_tokens=agent['completion_tokens'],
                ),
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

"""Token usage service — tracks agent-level token usage via repository."""

import logging

from domain.model.token_usage import LLMCallResult, TokenUsage
from port.token_usage_repository import TokenUsageRepository

logger = logging.getLogger(__name__)


def track_agent_usage(
    repo: TokenUsageRepository,
    agent_usage: list[tuple[str, LLMCallResult]],
    user_id: str,
    article_id: str | None,
    job_id: str,
) -> None:
    """Track token usage for each agent.

    Accepts a list of (agent_name, LLMCallResult) tuples.
    """
    try:
        total_saved = 0

        logger.info(
            "Agent usage retrieved",
            extra={
                "jobId": job_id,
                "agentCount": len(agent_usage),
                "usageData": [
                    {"name": name, "model": result.model, "tokens": result.total_tokens}
                    for name, result in agent_usage
                ]
            }
        )

        for agent_name, stats in agent_usage:
            if stats.total_tokens == 0:
                continue

            usage = TokenUsage.from_llm_result(
                stats, user_id,
                operation="article_generation",
                article_id=article_id,
                metadata={"job_id": job_id, "agent_name": agent_name},
            )
            if repo.save(usage):
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

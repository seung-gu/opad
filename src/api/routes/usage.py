"""Token usage API routes.

This module handles token usage tracking and analytics:
- GET /usage/me: Get current user's token usage summary
- GET /usage/articles/{article_id}: Get token usage for a specific article
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_article_repo, get_token_usage_repo
from api.security import get_current_user_required
from api.models import TokenUsageResponse, TokenUsageSummary, UserResponse
from port.article_repository import ArticleRepository
from port.token_usage_repository import TokenUsageRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me", response_model=TokenUsageSummary)
async def get_my_usage(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    current_user: UserResponse = Depends(get_current_user_required),
    repo: TokenUsageRepository = Depends(get_token_usage_repo),
):
    """Get current user's token usage summary.

    Returns aggregated token usage statistics for the authenticated user
    within the specified time window.

    Args:
        days: Number of days to look back (default: 30, range: 1-365)
        current_user: Authenticated user (required)

    Returns:
        TokenUsageSummary with total tokens, cost, breakdown by operation, and daily usage
    """
    summary = repo.get_user_summary(user_id=current_user.id, days=days)

    logger.info("Token usage summary retrieved", extra={
        "userId": current_user.id,
        "days": days,
        "totalTokens": summary.get("total_tokens", 0),
        "totalCost": summary.get("total_cost", 0.0)
    })

    return summary


@router.get("/articles/{article_id}", response_model=list[TokenUsageResponse])
async def get_article_usage(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    article_repo: ArticleRepository = Depends(get_article_repo),
    token_usage_repo: TokenUsageRepository = Depends(get_token_usage_repo),
):
    """Get token usage records for a specific article.

    Returns all token usage records associated with the specified article.
    Users can only access usage records for their own articles.

    Args:
        article_id: Article ID to get usage for
        current_user: Authenticated user (required)

    Returns:
        List of TokenUsageResponse objects sorted by created_at ascending
    """
    # Verify article ownership
    article = article_repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to access this article's usage")

    usage_records = token_usage_repo.get_by_article(article_id)

    logger.info("Article token usage retrieved", extra={
        "userId": current_user.id,
        "articleId": article_id,
        "recordCount": len(usage_records)
    })

    return usage_records

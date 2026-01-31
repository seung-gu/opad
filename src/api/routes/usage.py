"""Token usage API routes.

This module handles token usage tracking and analytics:
- GET /usage/me: Get current user's token usage summary
- GET /usage/articles/{article_id}: Get token usage for a specific article
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import get_current_user_required
from api.models import User, TokenUsageSummary, TokenUsageRecord, OperationUsage, DailyUsage
from utils.mongodb import get_user_token_summary, get_article_token_usage, get_article

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me", response_model=TokenUsageSummary)
async def get_my_usage(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user_required)
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
    summary = get_user_token_summary(user_id=current_user.id, days=days)

    # Convert by_operation dict to OperationUsage models
    by_operation = {}
    for op_name, op_data in summary.get('by_operation', {}).items():
        by_operation[op_name] = OperationUsage(
            tokens=op_data['tokens'],
            cost=op_data['cost'],
            count=op_data['count']
        )

    # Convert daily_usage list to DailyUsage models
    daily_usage = [
        DailyUsage(
            date=day['date'],
            tokens=day['tokens'],
            cost=day['cost']
        )
        for day in summary.get('daily_usage', [])
    ]

    logger.info("Token usage summary retrieved", extra={
        "userId": current_user.id,
        "days": days,
        "totalTokens": summary.get('total_tokens', 0),
        "totalCost": summary.get('total_cost', 0)
    })

    return TokenUsageSummary(
        total_tokens=summary.get('total_tokens', 0),
        total_cost=summary.get('total_cost', 0.0),
        by_operation=by_operation,
        daily_usage=daily_usage
    )


@router.get("/articles/{article_id}", response_model=list[TokenUsageRecord])
async def get_article_usage(
    article_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """Get token usage records for a specific article.

    Returns all token usage records associated with the specified article.
    Users can only access usage records for their own articles.

    Args:
        article_id: Article ID to get usage for
        current_user: Authenticated user (required)

    Returns:
        List of TokenUsageRecord objects sorted by created_at ascending
    """
    # Verify article ownership
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to access this article's usage")

    usage_records = get_article_token_usage(article_id)

    logger.info("Article token usage retrieved", extra={
        "userId": current_user.id,
        "articleId": article_id,
        "recordCount": len(usage_records)
    })

    return [
        TokenUsageRecord(
            id=record['id'],
            user_id=record['user_id'],
            operation=record['operation'],
            model=record['model'],
            prompt_tokens=record['prompt_tokens'],
            completion_tokens=record['completion_tokens'],
            total_tokens=record['total_tokens'],
            estimated_cost=record['estimated_cost'],
            metadata=record.get('metadata', {}),
            created_at=record['created_at']
        )
        for record in usage_records
    ]

"""Article-related API routes.

This module handles article creation and generation requests:
- POST /articles: Create article record
- POST /articles/:id/generate: Enqueue generation job
- GET /articles/:id: Get article details

Flow:
    Client → POST /articles → Create record → Return article_id
    Client → POST /articles/:id/generate → Enqueue job → Return job_id
    Client → Poll GET /jobs/:job_id → Get status → Wait for completion
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import sys
from pathlib import Path

# Add src to path
# articles.py is at /app/src/api/routes/articles.py
# src is at /app/src, so we go up 3 levels
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.models import ArticleResponse, GenerateRequest, GenerateResponse, JobResponse, ArticleListResponse, User
from api.middleware.auth import get_current_user_required
from api.job_queue import enqueue_job, update_job_status, get_job_status
from utils.mongodb import (
    save_article_metadata, 
    get_article, 
    get_mongodb_client, 
    find_duplicate_article,
    list_articles,
    delete_article,
    update_article_status
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


def _check_mongodb_connection() -> None:
    """Check MongoDB connection and raise if unavailable."""
    if not get_mongodb_client():
        raise HTTPException(status_code=503, detail="Database service unavailable")


def _validate_article(article_id: str) -> None:
    """Validate article exists in MongoDB."""
    _check_mongodb_connection()
    if not get_article(article_id):
        raise HTTPException(status_code=404, detail="Article not found")


def _parse_created_at(article: dict) -> datetime:
    """Parse created_at from article document.
    
    Handles both string (ISO format) and datetime objects.
    MongoDB may store as string, so we need to parse it.
    
    Returns:
        datetime: Always returns a datetime object. If created_at is missing or invalid,
                  returns current UTC time.
    """
    created_at = article.get('created_at')
    
    # Handle string (ISO format)
    if created_at and isinstance(created_at, str):
        # Replace 'Z' with '+00:00' for ISO format compatibility
        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    # Handle datetime object
    if created_at and isinstance(created_at, datetime):
        return created_at
    
    # Missing or invalid type: return current UTC time
    return datetime.now(timezone.utc)


def _build_article_response(article: dict) -> dict:
    """Build article response dict from MongoDB document.
    
    Extracts required fields from nested 'inputs' dict.
    Validates presence of required fields before accessing them.
    """
    # Validate required fields defensively
    inputs = article.get('inputs')
    if not inputs:
        article_id = article.get('_id', 'unknown')
        raise HTTPException(
            status_code=500,
            detail=f"Article data is incomplete: missing 'inputs' field (article_id: {article_id})"
        )
    
    created_at = _parse_created_at(article)
    # _parse_created_at always returns datetime, so we can safely format it
    
    # Format timestamp: timezone-aware datetimes already include timezone info in isoformat()
    if created_at.tzinfo is not None:
        # Timezone-aware: isoformat() returns '2025-01-13T12:34:56+00:00', don't add 'Z'
        formatted_time = created_at.isoformat()
    else:
        # Timezone-naive: isoformat() returns '2025-01-13T12:34:56', add 'Z' to indicate UTC
        formatted_time = created_at.isoformat() + 'Z'
    
    return {
        'id': article.get('_id'),
        'language': inputs['language'],
        'level': inputs['level'],
        'length': inputs['length'],
        'topic': inputs['topic'],
        'status': article.get('status'),
        'created_at': formatted_time,
        'user_id': article.get('user_id'),
        'job_id': article.get('job_id'),  # Include job_id for progress tracking
        'inputs': inputs
    }


def _prepare_inputs(request: GenerateRequest) -> dict:
    """Prepare job input data for CrewAI."""
    return {
        'language': request.language,
        'level': request.level,
        'length': request.length,
        'topic': request.topic
    }


def _check_duplicate(inputs: dict, force: bool = False, user_id: Optional[str] = None) -> None:
    """Check for duplicate articles and raise 409 if found (unless force=true).
    
    MongoDB-based duplicate detection: searches for articles with identical inputs
    created within the last 24 hours.
    
    This function performs duplicate detection BEFORE article creation to prevent
    empty articles from accumulating in MongoDB.
    
    Args:
        inputs: Job input parameters (language, level, length, topic)
        force: If True, skip duplicate check
        user_id: Owner ID for user-specific duplicate check
        
    Raises:
        HTTPException(409): If duplicate article exists and force=False
    """
    if force:
        logger.info("Force generation requested, skipping duplicate check", extra={"userId": user_id})
        return
    
    # MongoDB-based duplicate check
    existing_article = find_duplicate_article(inputs, user_id, hours=24)
    
    if not existing_article:
        return
    
    existing_article_id = existing_article.get('_id')
    existing_job_id = existing_article.get('job_id')
    
    logger.info("Duplicate article detected", extra={
        "existingArticleId": existing_article_id,
        "existingJobId": existing_job_id,
        "userId": user_id
    })
    
    # Get job status from Redis if job_id exists
    existing_job = None
    existing_job_data = None
    if existing_job_id:
        existing_job_data = get_job_status(existing_job_id)
        if existing_job_data:
            try:
                existing_job = JobResponse(**existing_job_data)
            except Exception as e:
                logger.warning("Failed to parse existing job status", extra={
                    "existingJobId": existing_job_id,
                    "error": str(e)
                })
    
    detail = {
        "error": "Duplicate article detected",
        "message": "An article with identical parameters was created within the last 24 hours.",
        "existing_job": existing_job.model_dump(mode='json') if existing_job else None,
        "article_id": existing_article_id
    }
    
    raise HTTPException(status_code=409, detail=detail)


def _create_and_enqueue_job(article_id: str, inputs: dict, job_id: str, user_id: Optional[str] = None) -> GenerateResponse:
    """Create new job and enqueue it.
    
    Args:
        article_id: Article ID
        inputs: Job input parameters
        job_id: Job ID (generated by caller)
        user_id: Owner ID for logging
    
    Critical: Status must be created BEFORE enqueueing to prevent orphaned jobs.
    If status creation fails, we haven't queued the job yet (no orphan).
    If enqueue fails after status creation, status shows 'queued' but worker never picks it up
    (visible failure state, better than orphaned processing job with no status).
    """
    # Step 1: Initialize job status FIRST (before enqueueing)
    if not update_job_status(job_id, 'queued', 0, 'Job queued, waiting for worker...', article_id=article_id):
        logger.error("Failed to initialize job status", extra={"jobId": job_id, "articleId": article_id})
        raise HTTPException(status_code=503, detail="Failed to initialize job status")
    
    # Step 2: Enqueue job to Redis queue
    # If this fails, status exists but job won't be processed (visible failure state)
    if not enqueue_job(job_id, article_id, inputs):
        update_job_status(job_id, 'failed', 0, 'Failed to enqueue job', 'Queue service unavailable', article_id=article_id)
        # Update MongoDB Article status to 'failed'
        update_article_status(article_id, 'failed')
        raise HTTPException(status_code=503, detail="Failed to enqueue job")
    
    logger.info("Job enqueued", extra={"jobId": job_id, "articleId": article_id, "userId": user_id})
    return GenerateResponse(
        job_id=job_id,
        article_id=article_id,
        message="Article generation started. Use job_id to track progress."
    )


@router.get("")
async def list_articles_endpoint(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    language: Optional[str] = None,
    level: Optional[str] = None,
    current_user: User = Depends(get_current_user_required)
):
    """Get article list with filters and pagination.

    Returns only articles owned by the authenticated user.

    Query parameters:
        skip: Number of articles to skip (default: 0)
        limit: Maximum number of articles to return (default: 20, max: 100)
        status: Filter by status (optional)
        language: Filter by language (optional)
        level: Filter by level (optional)

    Returns:
        ArticleListResponse with articles, total count, and pagination info

    Raises:
        HTTPException: 401 if user is not authenticated
    """
    _check_mongodb_connection()

    # Validate limit
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1

    # Get articles from MongoDB - automatically filter by current user
    # By default, exclude soft-deleted articles unless status='deleted' is explicitly requested
    articles, total = list_articles(skip, limit, status, language, level, current_user.id, exclude_deleted=True)
    
    # Build response list
    article_responses = []
    for article in articles:
        try:
            article_responses.append(_build_article_response(article))
        except Exception as e:
            # Skip invalid articles (log but don't fail entire request)
            logger.warning("Skipping invalid article", extra={
                "articleId": article.get('_id'),
                "error": str(e)
            })
    
    logger.info("Listed articles", extra={
        "count": len(article_responses),
        "total": total,
        "skip": skip,
        "limit": limit
    })
    
    return ArticleListResponse(
        articles=article_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_article(
    request: GenerateRequest,
    force: bool = False,
    current_user: User = Depends(get_current_user_required)
):
    """Create article and start generation (unified endpoint).

    This endpoint combines article creation and job enqueueing to prevent
    creating empty articles when duplicates are detected.

    Requires authentication - all articles are owned by the authenticated user.

    Args:
        request: Article generation parameters
        force: If True, skip duplicate check and create new article + job
        current_user: Authenticated user (required)

    Returns:
        GenerateResponse with job_id and article_id

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 409 if duplicate job exists (with existing_job info for user decision)
    """
    _check_mongodb_connection()
    inputs = _prepare_inputs(request)

    # Extract user_id from JWT token - authentication is now required
    user_id: str = current_user.id
    
    logger.info(
        "Article generation requested",
        extra={
            "userId": user_id,
            "topic": request.topic,
            "language": request.language
        }
    )
    
    # Step 1: Check for duplicate BEFORE creating article (user-specific)
    _check_duplicate(inputs, force, user_id)  # Raises HTTPException(409) if duplicate - ceased here
    
    # Step 2: No duplicate (or force=true) → generate IDs
    article_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    
    # Step 3: Create article with job_id
    if not save_article_metadata(
        article_id=article_id,
        language=request.language,
        level=request.level,
        length=request.length,
        topic=request.topic,
        status='running',
        created_at=created_at,
        user_id=user_id,
        job_id=job_id
    ):
        raise HTTPException(status_code=503, detail="Failed to save article")
    
    logger.info("Created article", extra={"articleId": article_id, "jobId": job_id, "userId": user_id})
    
    # Step 4: Enqueue job
    return _create_and_enqueue_job(article_id, inputs, job_id, user_id)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """Get article metadata by ID.

    Requires authentication - users can only access their own articles.

    Args:
        article_id: ID of the article to retrieve
        current_user: Authenticated user (required)

    Returns:
        ArticleResponse with article metadata

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 403 if user doesn't own the article
        HTTPException: 404 if article not found or soft-deleted
    """
    _validate_article(article_id)

    article_doc = get_article(article_id)
    if not article_doc:
        # Race condition: article was deleted between validation and fetch
        raise HTTPException(status_code=404, detail="Article not found")

    # Check if article is soft-deleted
    if article_doc.get('status') == 'deleted':
        raise HTTPException(status_code=404, detail="Article not found")

    # Check ownership
    article_user_id = article_doc.get('user_id')
    if article_user_id != current_user.id:
        logger.warning(
            "Unauthorized access attempt",
            extra={
                "articleId": article_id,
                "articleUserId": article_user_id,
                "requestUserId": current_user.id
            }
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this article"
        )

    response_data = _build_article_response(article_doc)
    return ArticleResponse(**response_data)


@router.get("/{article_id}/content")
async def get_article_content(
    article_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """Get article content (markdown) from MongoDB.

    Requires authentication - users can only access their own articles.

    Args:
        article_id: ID of the article to retrieve content for
        current_user: Authenticated user (required)

    Returns:
        Markdown content of the article

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 403 if user doesn't own the article
        HTTPException: 404 if article not found, soft-deleted, or content not available
    """
    from fastapi.responses import Response

    _validate_article(article_id)

    article_doc = get_article(article_id)
    if not article_doc:
        # Race condition: article was deleted between validation and fetch
        raise HTTPException(status_code=404, detail="Article not found")

    # Check if article is soft-deleted
    if article_doc.get('status') == 'deleted':
        raise HTTPException(status_code=404, detail="Article not found")

    # Check ownership
    article_user_id = article_doc.get('user_id')
    if article_user_id != current_user.id:
        logger.warning(
            "Unauthorized content access attempt",
            extra={
                "articleId": article_id,
                "articleUserId": article_user_id,
                "requestUserId": current_user.id
            }
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this article"
        )

    content = article_doc.get('content')
    if not content:
        raise HTTPException(status_code=404, detail="Article content not found")

    return Response(content=content, media_type='text/markdown')


@router.delete("/{article_id}")
async def delete_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """Soft delete article by setting status='deleted'.

    Requires authentication - users can only delete their own articles.

    Soft delete preserves data for potential recovery and audit trail.
    Article remains in database but is marked as deleted.

    Args:
        article_id: ID of the article to delete
        current_user: Authenticated user (required)

    Returns:
        Success message with deleted article_id

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 403 if user doesn't own the article
        HTTPException: 404 if article not found
    """
    _validate_article(article_id)

    # Check ownership
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article_user_id = article.get('user_id')
    if article_user_id != current_user.id:
        logger.warning(
            "Unauthorized delete attempt",
            extra={
                "articleId": article_id,
                "articleUserId": article_user_id,
                "requestUserId": current_user.id
            }
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this article"
        )

    success = delete_article(article_id)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to delete article")

    logger.info("Article deleted via API", extra={"articleId": article_id, "userId": current_user.id})

    return {
        "success": True,
        "article_id": article_id,
        "message": "Article soft deleted (status='deleted')"
    }

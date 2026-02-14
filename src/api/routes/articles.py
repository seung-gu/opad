"""Article-related API routes.

This module handles article creation and generation requests:
- POST /articles: Create article record
- POST /articles/:id/generate: Enqueue generation job
- GET /articles/:id: Get article details

Flow:
    Client -> POST /articles -> Create record -> Return article_id
    Client -> POST /articles/:id/generate -> Enqueue job -> Return job_id
    Client -> Poll GET /jobs/:job_id -> Get status -> Wait for completion
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from api.models import ArticleResponse, GenerateRequest, GenerateResponse, JobResponse, ArticleListResponse, User, VocabularyResponse
from api.middleware.auth import get_current_user_required
from api.job_queue import enqueue_job, update_job_status, get_job_status
from api.dependencies import get_article_repo
from port.article_repository import ArticleRepository
from domain.model.article import ArticleInputs, ArticleStatus, Article
from utils.mongodb import get_vocabularies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


def _build_article_response(article: Article) -> dict:
    """Build article response dict from Article domain model."""
    created_at = article.created_at

    # Format timestamp
    if created_at.tzinfo is not None:
        formatted_time = created_at.isoformat()
    else:
        formatted_time = created_at.isoformat() + 'Z'

    return {
        'id': article.id,
        'language': article.inputs.language,
        'level': article.inputs.level,
        'length': article.inputs.length,
        'topic': article.inputs.topic,
        'status': article.status.value if isinstance(article.status, ArticleStatus) else article.status,
        'created_at': formatted_time,
        'user_id': article.user_id,
        'job_id': article.job_id,
        'inputs': {
            'language': article.inputs.language,
            'level': article.inputs.level,
            'length': article.inputs.length,
            'topic': article.inputs.topic,
        }
    }


def _check_ownership(article: Article, current_user: User, article_id: str, action: str = "access") -> None:
    """Check if the current user owns the article."""
    if article.user_id != current_user.id:
        logger.warning(
            f"Unauthorized {action} attempt",
            extra={
                "articleId": article_id,
                "articleUserId": article.user_id,
                "requestUserId": current_user.id
            }
        )
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to {action} this article"
        )


def _get_article_or_404(
    repo: ArticleRepository, article_id: str, check_deleted: bool = True
) -> Article:
    """Retrieve article or raise 404."""
    article = repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if check_deleted and article.status == ArticleStatus.DELETED:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _check_duplicate(
    repo: ArticleRepository,
    inputs: ArticleInputs,
    force: bool = False,
    user_id: Optional[str] = None,
) -> None:
    """Check for duplicate articles and raise 409 if found."""
    if force:
        logger.info("Force generation requested, skipping duplicate check", extra={"userId": user_id})
        return

    existing = repo.find_duplicate(inputs, user_id, hours=24)
    if not existing:
        return

    logger.info("Duplicate article detected", extra={
        "existingArticleId": existing.id,
        "existingJobId": existing.job_id,
        "userId": user_id
    })

    # Get job status from Redis if job_id exists
    existing_job = None
    if existing.job_id:
        existing_job_data = get_job_status(existing.job_id)
        if existing_job_data:
            try:
                existing_job = JobResponse(**existing_job_data)
            except Exception as e:
                logger.warning("Failed to parse existing job status", extra={
                    "existingJobId": existing.job_id,
                    "error": str(e)
                })

    detail = {
        "error": "Duplicate article detected",
        "message": "An article with identical parameters was created within the last 24 hours.",
        "existing_job": existing_job.model_dump(mode='json') if existing_job else None,
        "article_id": existing.id
    }

    raise HTTPException(status_code=409, detail=detail)


def _create_and_enqueue_job(
    repo: ArticleRepository,
    article_id: str,
    inputs: dict,
    job_id: str,
    user_id: Optional[str] = None,
) -> GenerateResponse:
    """Create new job and enqueue it."""
    if not update_job_status(job_id, 'queued', 0, 'Job queued, waiting for worker...', article_id=article_id):
        logger.error("Failed to initialize job status", extra={"jobId": job_id, "articleId": article_id})
        raise HTTPException(status_code=503, detail="Failed to initialize job status")

    if not enqueue_job(job_id, article_id, inputs, user_id):
        update_job_status(job_id, 'failed', 0, 'Failed to enqueue job', 'Queue service unavailable', article_id=article_id)
        repo.update_status(article_id, ArticleStatus.FAILED)
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
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article list with filters and pagination."""
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1

    try:
        status_enum = ArticleStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status}")
    articles, total = repo.find_many(
        skip, limit, status_enum, language, level, current_user.id, exclude_deleted=True,
    )

    article_responses = []
    for article in articles:
        try:
            article_responses.append(_build_article_response(article))
        except Exception as e:
            logger.warning("Skipping invalid article", extra={
                "articleId": article.id,
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
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Create article and start generation (unified endpoint)."""
    inputs = ArticleInputs(
        language=request.language,
        level=request.level,
        length=request.length,
        topic=request.topic,
    )
    user_id: str = current_user.id

    logger.info("Article generation requested", extra={
        "userId": user_id,
        "topic": request.topic,
        "language": request.language
    })

    # Step 1: Check for duplicate
    _check_duplicate(repo, inputs, force, user_id)

    # Step 2: Generate IDs
    article_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    # Step 3: Create article
    if not repo.save_metadata(
        article_id=article_id,
        inputs=inputs,
        status=ArticleStatus.RUNNING,
        created_at=created_at,
        user_id=user_id,
        job_id=job_id,
    ):
        raise HTTPException(status_code=503, detail="Failed to save article")

    logger.info("Created article", extra={"articleId": article_id, "jobId": job_id, "userId": user_id})

    # Step 4: Enqueue job
    job_inputs = {
        'language': request.language,
        'level': request.level,
        'length': request.length,
        'topic': request.topic,
    }
    return _create_and_enqueue_job(repo, article_id, job_inputs, job_id, user_id)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article metadata by ID."""
    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id)

    response_data = _build_article_response(article)
    return ArticleResponse(**response_data)


@router.get("/{article_id}/content")
async def get_article_content(
    article_id: str,
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article content (markdown)."""
    from fastapi.responses import Response

    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id, "access")

    if not article.content:
        raise HTTPException(status_code=404, detail="Article content not found")

    return Response(content=article.content, media_type='text/markdown')


@router.get("/{article_id}/vocabularies", response_model=list[VocabularyResponse])
async def get_article_vocabularies(
    article_id: str,
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get vocabularies for a specific article."""
    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id, "access")

    vocabularies = get_vocabularies(
        article_id=article_id,
        user_id=current_user.id
    )

    logger.info("Article vocabularies retrieved", extra={
        "articleId": article_id,
        "count": len(vocabularies),
        "userId": current_user.id
    })

    return vocabularies


@router.delete("/{article_id}")
async def delete_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Soft delete article."""
    article = _get_article_or_404(repo, article_id, check_deleted=False)
    _check_ownership(article, current_user, article_id, "delete")

    success = repo.delete(article_id)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to delete article")

    logger.info("Article deleted via API", extra={"articleId": article_id, "userId": current_user.id})

    return {
        "success": True,
        "article_id": article_id,
        "message": "Article soft deleted (status='deleted')"
    }

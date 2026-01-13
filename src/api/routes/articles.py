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
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

# Add src to path
# articles.py is at /app/src/api/routes/articles.py
# src is at /app/src, so we go up 3 levels
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.models import ArticleCreate, ArticleResponse, GenerateRequest, GenerateResponse, JobResponse
from api.queue import enqueue_job, update_job_status, get_job_status
from utils.mongodb import save_article_metadata, get_article, get_mongodb_client, get_latest_article
import hashlib
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])

# Redis constants for duplicate detection
PARAMS_HASH_PREFIX = 'opad:params_hash:'
PARAMS_HASH_TTL = 86400  # 24 hours in seconds


def _calculate_params_hash(inputs: dict) -> str:
    """Calculate SHA256 hash of sorted JSON inputs for duplicate detection."""
    sorted_inputs = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(sorted_inputs.encode('utf-8')).hexdigest()


def _check_duplicate_job(params_hash: str) -> Optional[str]:
    """Check if a job with the same params_hash exists (within 24 hours)."""
    from api.queue import get_redis_client
    from redis.exceptions import RedisError
    
    client = get_redis_client()
    if not client:
        return None
    
    try:
        hash_key = f"{PARAMS_HASH_PREFIX}{params_hash}"
        existing_job_id = client.get(hash_key)
        return existing_job_id if existing_job_id else None
    except RedisError as e:
        logger.error("Failed to check duplicate job", extra={"paramsHash": params_hash, "error": str(e)})
        return None


def _store_params_hash(params_hash: str, job_id: str) -> bool:
    """Store params_hash in Redis with 24-hour TTL."""
    from api.queue import get_redis_client
    from redis.exceptions import RedisError
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        hash_key = f"{PARAMS_HASH_PREFIX}{params_hash}"
        client.setex(hash_key, PARAMS_HASH_TTL, job_id)
        logger.debug("Stored params_hash", extra={"paramsHash": params_hash, "jobId": job_id})
        return True
    except RedisError as e:
        logger.error("Failed to store params_hash", extra={"paramsHash": params_hash, "jobId": job_id, "error": str(e)})
        return False


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
    """
    created_at = article.get('created_at')
    if created_at and isinstance(created_at, str):
        # Replace 'Z' with '+00:00' for ISO format compatibility
        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    return created_at if created_at else datetime.utcnow()


def _build_article_response(article: dict) -> dict:
    """Build article response dict from MongoDB document."""
    inputs = article.get('inputs', {})
    created_at = _parse_created_at(article)
    
    # Format timestamp: timezone-aware datetimes already include timezone info in isoformat()
    if isinstance(created_at, datetime):
        if created_at.tzinfo is not None:
            # Timezone-aware: isoformat() returns '2025-01-13T12:34:56+00:00', don't add 'Z'
            formatted_time = created_at.isoformat()
        else:
            # Timezone-naive: isoformat() returns '2025-01-13T12:34:56', add 'Z' to indicate UTC
            formatted_time = created_at.isoformat() + 'Z'
    else:
        formatted_time = created_at
    
    return {
        'id': article.get('_id'),
        'language': inputs.get('language'),
        'level': inputs.get('level'),
        'length': inputs.get('length'),
        'topic': inputs.get('topic'),
        'status': article.get('status', 'pending'),
        'created_at': formatted_time,
        'owner_id': article.get('owner_id'),
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


def _handle_duplicate(article_id: str, inputs: dict, force: bool = False) -> None:
    """Check for duplicate job and raise HTTPException if found.
    
    Args:
        force: If True, skip duplicate check and allow new job creation.
    
    Raises HTTP 409 Conflict with existing_job information for user decision.
    The existing_job contains status (succeeded, running, failed, queued) and progress.
    """
    if force:
        logger.info("Force generation requested, skipping duplicate check", extra={"articleId": article_id})
        return
    
    params_hash = _calculate_params_hash(inputs)
    existing_job_id = _check_duplicate_job(params_hash)
    
    if not existing_job_id:
        return
    
    logger.info("Duplicate job detected", extra={"articleId": article_id, "existingJobId": existing_job_id})
    
    existing_job_data = get_job_status(existing_job_id)
    existing_job = None
    if existing_job_data:
        try:
            existing_job = JobResponse(**existing_job_data)
        except Exception as e:
            logger.warning("Failed to parse existing job status", extra={"existingJobId": existing_job_id, "error": str(e)})
    
    # Build error detail with existing job information for frontend
    detail = {
        "error": "Duplicate job detected",
        "message": "A job with identical parameters was created within the last 24 hours.",
        "existing_job": existing_job.dict() if existing_job else None,
        "article_id": article_id
    }
    
    raise HTTPException(status_code=409, detail=detail)


def _create_and_enqueue_job(article_id: str, inputs: dict) -> GenerateResponse:
    """Create new job and enqueue it.
    
    Critical: Status must be created BEFORE enqueueing to prevent orphaned jobs.
    If status creation fails, we haven't queued the job yet (no orphan).
    If enqueue fails after status creation, status shows 'queued' but worker never picks it up
    (visible failure state, better than orphaned processing job with no status).
    
    Also critical: params_hash must be stored AFTER job status is successfully created.
    If status creation fails, params_hash should not be stored to prevent orphaned duplicate detection.
    """
    job_id = str(uuid.uuid4())
    params_hash = _calculate_params_hash(inputs)
    
    # Step 1: Initialize job status FIRST (before storing params_hash and enqueueing)
    # If this fails, we don't store params_hash, preventing orphaned duplicate detection
    if not update_job_status(job_id, 'queued', 0, 'Job queued, waiting for worker...', article_id=article_id):
        logger.error("Failed to initialize job status", extra={"jobId": job_id, "articleId": article_id})
        raise HTTPException(status_code=503, detail="Failed to initialize job status")
    
    # Step 1.5: Store params_hash AFTER status is successfully created
    # This ensures that if duplicate detection finds this job, get_job_status will return valid data
    # Critical: params_hash storage must succeed for duplicate detection to work
    if not _store_params_hash(params_hash, job_id):
        logger.error("Failed to store params_hash", extra={"jobId": job_id, "articleId": article_id})
        # Don't fail the entire request, but log the error
        # Duplicate detection will not work for this job, but job can still proceed
        # This is a degraded state, but better than failing the entire generation
    
    # Step 2: Enqueue job to Redis queue
    # If this fails, status exists but job won't be processed (visible failure state)
    if not enqueue_job(job_id, article_id, inputs):
        update_job_status(job_id, 'failed', 0, 'Failed to enqueue job', 'Queue service unavailable', article_id=article_id)
        raise HTTPException(status_code=503, detail="Failed to enqueue job")
    
    logger.info("Job enqueued", extra={"jobId": job_id, "articleId": article_id})
    return GenerateResponse(
        job_id=job_id,
        article_id=article_id,
        message="Article generation started. Use job_id to track progress."
    )


@router.get("/latest")
async def get_latest_article_endpoint():
    """Get the most recently created article."""
    _check_mongodb_connection()
    
    article = get_latest_article()
    if not article:
        raise HTTPException(status_code=404, detail="No articles found")
    
    logger.info("Retrieved latest article", extra={"articleId": article.get('_id')})
    return _build_article_response(article)


@router.post("", response_model=ArticleResponse, status_code=201)
async def create_article(article: ArticleCreate):
    """Create a new article record.
    
    Generates created_at timestamp locally BEFORE saving to eliminate race condition
    between save and fetch operations. Returns response using local timestamp.
    """
    article_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    inputs = {
        'language': article.language,
        'level': article.level,
        'length': article.length,
        'topic': article.topic
    }
    
    if not save_article_metadata(
        article_id=article_id,
        language=article.language,
        level=article.level,
        length=article.length,
        topic=article.topic,
        status='pending',
        created_at=created_at,
        owner_id=article.owner_id
    ):
        raise HTTPException(status_code=503, detail="Failed to save article")
    
    logger.info("Created article", extra={"articleId": article_id})
    return ArticleResponse(
        id=article_id,
        language=article.language,
        level=article.level,
        length=article.length,
        topic=article.topic,
        status='pending',
        created_at=created_at,
        owner_id=article.owner_id,
        inputs=inputs
    )


@router.post("/{article_id}/generate", response_model=GenerateResponse)
async def generate_article(article_id: str, request: GenerateRequest, force: bool = False):
    """Start article generation by enqueueing a job.
    
    Args:
        force: If True, skip duplicate check and create new job even if duplicate exists.
    
    Returns 409 Conflict if duplicate job exists (with existing_job info for user decision).
    """
    _validate_article(article_id)
    inputs = _prepare_inputs(request)
    
    _handle_duplicate(article_id, inputs, force=force)  # Raises HTTPException(409) if duplicate
    
    return _create_and_enqueue_job(article_id, inputs)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_endpoint(article_id: str):
    """Get article metadata by ID."""
    _validate_article(article_id)
    
    article_doc = get_article(article_id)
    if not article_doc:
        # Race condition: article was deleted between validation and fetch
        raise HTTPException(status_code=404, detail="Article not found")
    
    response_data = _build_article_response(article_doc)
    return ArticleResponse(**response_data)


@router.get("/{article_id}/content")
async def get_article_content(article_id: str):
    """Get article content (markdown) from MongoDB."""
    from fastapi.responses import Response
    
    _validate_article(article_id)
    
    article_doc = get_article(article_id)
    if not article_doc:
        # Race condition: article was deleted between validation and fetch
        raise HTTPException(status_code=404, detail="Article not found")
    
    content = article_doc.get('content')
    if not content:
        raise HTTPException(status_code=404, detail="Article content not found")
    
    return Response(content=content, media_type='text/markdown')

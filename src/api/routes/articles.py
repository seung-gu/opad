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
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

# Add src to path
# articles.py is at /app/src/api/routes/articles.py
# src is at /app/src, so we go up 3 levels
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.models import ArticleCreate, ArticleResponse, GenerateRequest, GenerateResponse
from api.queue import enqueue_job, update_job_status
from utils.mongodb import save_article_metadata, get_article, get_mongodb_client, get_latest_article

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/latest")
async def get_latest_article_endpoint():
    """Get the most recently created article.
    
    This endpoint is used by the frontend on page load to restore
    the last article the user was viewing.
    
    Returns:
        Article metadata and content if available, or 404 if no articles exist
    """
    # Check MongoDB connection first
    client = get_mongodb_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    
    article = get_latest_article()
    
    if not article:
        raise HTTPException(
            status_code=404,
            detail="No articles found"
        )
    
    article_id = article.get('_id')
    logger.info("Retrieved latest article", extra={"articleId": article_id})
    
    return {
        'id': article.get('_id'),
        'language': article.get('language'),
        'level': article.get('level'),
        'length': article.get('length'),
        'topic': article.get('topic'),
        'status': article.get('status', 'pending'),
        'created_at': article.get('created_at', datetime.utcnow()).isoformat() + 'Z'
    }


@router.post("", response_model=ArticleResponse, status_code=201)
async def create_article(article: ArticleCreate):
    """Create a new article record.
    
    This creates a metadata record for the article. The actual content
    is generated later by the worker when /generate is called.
    
    Flow:
        1. Generate unique article_id (UUID)
        2. Store article metadata (language, level, length, topic)
        3. Return article_id to client
        4. Client then calls POST /articles/:id/generate to start generation
    
    Storage:
        - MongoDB: Article metadata stored persistently
    
    Args:
        article: Article creation request (language, level, length, topic)
        
    Returns:
        ArticleResponse with article_id and metadata
    """
    article_id = str(uuid.uuid4())
    
    # Generate created_at timestamp locally BEFORE saving
    # This eliminates the race condition window between save and fetch operations
    created_at = datetime.utcnow()
    
    # Save metadata to MongoDB with pre-generated timestamp
    success = save_article_metadata(
        article_id=article_id,
        language=article.language,
        level=article.level,
        length=article.length,
        topic=article.topic,
        status='pending',
        created_at=created_at
    )
    
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to save article. Database service unavailable."
        )
    
    logger.info("Created article", extra={"articleId": article_id})
    
    # Return response using local timestamp - no need to fetch from DB
    # This eliminates the race condition and prevents orphaned records
    return ArticleResponse(
        id=article_id,
        language=article.language,
        level=article.level,
        length=article.length,
        topic=article.topic,
        status='pending',
        created_at=created_at
    )


@router.post("/{article_id}/generate", response_model=GenerateResponse)
async def generate_article(article_id: str, request: GenerateRequest):
    """Start article generation by enqueueing a job.
    
    Key concept: Asynchronous processing
        - This endpoint returns immediately with a job_id
        - Actual generation happens in the background (worker)
        - Client polls GET /jobs/:job_id to track progress
    
    Why async?
        - CrewAI takes 2-5 minutes to generate an article
        - HTTP requests would timeout if we waited
        - Job queue pattern allows long-running tasks
    
    Flow:
        1. Validate article exists
        2. Generate unique job_id
        3. Enqueue job to Redis (RPUSH to queue)
        4. Initialize job status in Redis (SET status key)
        5. Return job_id to client immediately
        6. Worker picks up job (BLPOP from queue)
        7. Worker executes CrewAI and updates status
        8. Client polls status until completion
    
    Critical operations:
        - Both enqueue_job() and update_job_status() must succeed
        - If enqueue succeeds but status init fails, client will poll forever
        - If either fails, return 503 (service unavailable)
    
    Args:
        article_id: Article ID (must exist in MongoDB)
        request: Generation parameters (language, level, length, topic)
        
    Returns:
        GenerateResponse with job_id for status tracking
        
    Raises:
        404: Article not found
        503: Redis unavailable (queue or status update failed)
    """
    # Validate article exists in MongoDB
    # Check MongoDB connection first to distinguish connection failure from "not found"
    if not get_mongodb_client():
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Cannot validate article."
        )
    
    article_doc = get_article(article_id)
    if not article_doc:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Prepare job input data for CrewAI
    inputs = {
        'language': request.language,
        'level': request.level,
        'length': request.length,
        'topic': request.topic
    }
    
    # Step 1: Initialize job status in Redis FIRST
    # Critical: Must create status before enqueuing to prevent orphaned jobs
    # If status creation fails, we haven't queued the job yet, so no orphan
    # If enqueue fails after this, status will show 'queued' but worker never picks it up
    # This is safer than the reverse (orphaned processing job with no status)
    status_updated = update_job_status(
        job_id=job_id,
        status='queued',
        progress=0,
        message='Job queued, waiting for worker...',
        article_id=article_id
    )
    if not status_updated:
        logger.error("Failed to initialize job status", extra={"jobId": job_id, "articleId": article_id})
        raise HTTPException(
            status_code=503,
            detail="Failed to initialize job status. Queue service unavailable."
        )
    
    # Step 2: Enqueue job to Redis queue
    # Now that status exists, enqueue the job for worker to pick up
    # If this fails, status exists but job won't be processed (visible failure state)
    success = enqueue_job(job_id, article_id, inputs)
    if not success:
        # Update status to 'failed' since we couldn't enqueue
        update_job_status(
            job_id=job_id,
            status='failed',
            progress=0,
            message='Failed to enqueue job',
            error='Queue service unavailable',
            article_id=article_id
        )
        raise HTTPException(
            status_code=503,
            detail="Failed to enqueue job. Queue service unavailable."
        )
    
    logger.info("Job enqueued", extra={"jobId": job_id, "articleId": article_id})
    
    return GenerateResponse(
        job_id=job_id,
        article_id=article_id,
        message="Article generation started. Use job_id to track progress."
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_endpoint(article_id: str):
    """Get article metadata by ID.
    
    Returns article metadata (language, level, length, topic, status).
    Does NOT return generated content (use GET /articles/:id/content for that).
    
    Args:
        article_id: Article ID
        
    Returns:
        ArticleResponse with metadata
        
    Raises:
        404: Article not found
        503: Database service unavailable
    """
    # Check MongoDB connection first to distinguish connection failure from "not found"
    if not get_mongodb_client():
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Cannot retrieve article."
        )
    
    article_doc = get_article(article_id)
    if not article_doc:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return ArticleResponse(
        id=article_doc['_id'],
        language=article_doc['language'],
        level=article_doc['level'],
        length=article_doc['length'],
        topic=article_doc['topic'],
        status=article_doc.get('status', 'pending'),
        created_at=article_doc.get('created_at', datetime.utcnow())
    )


@router.get("/{article_id}/content")
async def get_article_content(article_id: str):
    """Get article content (markdown) from MongoDB.
    
    This endpoint returns the generated article content as markdown text.
    Used by the web service to display the article.
    
    Args:
        article_id: Article ID
        
    Returns:
        Markdown content as plain text
        
    Raises:
        404: Article not found or content not available
        503: Database service unavailable
    """
    from fastapi.responses import Response
    
    # Check MongoDB connection first to distinguish connection failure from "not found"
    if not get_mongodb_client():
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Cannot retrieve article content."
        )
    
    article_doc = get_article(article_id)
    if not article_doc:
        raise HTTPException(status_code=404, detail="Article not found")
    
    content = article_doc.get('content')
    if not content:
        raise HTTPException(
            status_code=404, 
            detail="Article content not found. Article may not be generated yet."
        )
    
    return Response(
        content=content,
        media_type='text/markdown'
    )

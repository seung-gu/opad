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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])

# In-memory storage (temporary - will be replaced with Postgres)
# TODO: Issue #8 - Migrate to Postgres database
# Current limitation: Data lost on service restart
_articles_store: dict[str, dict] = {}


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
        - Currently: In-memory dict (lost on restart)
        - TODO: Issue #8 - Migrate to Postgres
    
    Args:
        article: Article creation request (language, level, length, topic)
        
    Returns:
        ArticleResponse with article_id and metadata
    """
    article_id = str(uuid.uuid4())
    article_data = {
        'id': article_id,
        'language': article.language,
        'level': article.level,
        'length': article.length,
        'topic': article.topic,
        'status': 'pending',  # Will be updated to 'generating' when job starts
        'created_at': datetime.now()
    }
    
    _articles_store[article_id] = article_data
    logger.info(f"Created article {article_id}")
    
    return ArticleResponse(**article_data)


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
        article_id: Article ID (must exist in _articles_store)
        request: Generation parameters (language, level, length, topic)
        
    Returns:
        GenerateResponse with job_id for status tracking
        
    Raises:
        404: Article not found
        503: Redis unavailable (queue or status update failed)
    """
    # Validate article exists
    if article_id not in _articles_store:
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
    
    # Step 1: Enqueue job to Redis queue
    # This adds the job to the queue for worker to pick up
    success = enqueue_job(job_id, article_id, inputs)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to enqueue job. Queue service unavailable."
        )
    
    # Step 2: Initialize job status in Redis
    # Critical: Client will poll this status, so it must exist
    # If this fails, client will poll forever for non-existent status
    status_updated = update_job_status(
        job_id=job_id,
        status='queued',
        progress=0,
        message='Job queued, waiting for worker...',
        article_id=article_id
    )
    if not status_updated:
        # Job is enqueued but status init failed
        # Raise error to prevent client from getting job_id
        # TODO: Consider dequeuing the job or implementing cleanup
        logger.error(f"Failed to update job status for {job_id} after enqueue")
        raise HTTPException(
            status_code=503,
            detail="Failed to initialize job status. Queue service unavailable."
        )
    
    logger.info(f"Job {job_id} enqueued for article {article_id}")
    
    return GenerateResponse(
        job_id=job_id,
        article_id=article_id,
        message="Article generation started. Use job_id to track progress."
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str):
    """Get article metadata by ID.
    
    Returns article metadata (language, level, length, topic, status).
    Does NOT return generated content (that's stored in R2).
    
    Args:
        article_id: Article ID
        
    Returns:
        ArticleResponse with metadata
        
    Raises:
        404: Article not found
    """
    if article_id not in _articles_store:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return ArticleResponse(**_articles_store[article_id])

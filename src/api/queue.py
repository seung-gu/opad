"""Redis queue management for job processing.

This module manages the job queue system using Redis:
- Queue: FIFO list of pending jobs (RPUSH + BLPOP)
- Status: Individual job status tracking with 24h TTL
- Connection: Cached client with automatic reconnection

Architecture:
    API Service → enqueue_job() → Redis Queue → dequeue_job() → Worker Service
                ↓                                                    ↓
            update_job_status() ← Redis Status ← update_job_status()
                ↑
            get_job_status() ← Client polling
"""

import json
import logging
import os
from typing import Optional
from datetime import datetime
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Redis connection - Railway provides complete REDIS_URL
REDIS_URL = os.getenv('REDIS_URL', '')
QUEUE_NAME = 'opad:jobs'  # Redis List: stores pending jobs in FIFO order

# Connection caching and failure tracking
# - Cache successful connections to avoid repeated connection attempts
# - Track initial connection failure (config issue) vs transient failures (network)
_redis_client_cache = None
_redis_connection_attempted = False  # True after first successful connection
_redis_connection_failed = False     # True if initial connection failed (config issue)


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client connection with caching and reconnection logic.
    
    Connection strategy:
    1. Return cached client if healthy (ping succeeds)
    2. If cached client fails, attempt reconnection
    3. If initial connection failed (config issue), don't retry
    
    This prevents:
    - Repeated connection attempts on every call (performance)
    - Log spam from transient network failures (noise)
    - Retry attempts when Redis is misconfigured (futile)
    
    Returns:
        Redis client or None if connection fails
    """
    global _redis_client_cache, _redis_connection_attempted, _redis_connection_failed
    
    # Fast path: return cached client if healthy
    if _redis_client_cache:
        try:
            _redis_client_cache.ping()
            return _redis_client_cache
        except:
            # Cached client is stale (network issue), clear and reconnect
            _redis_client_cache = None
            logger.debug("[REDIS] Cached client failed ping, attempting reconnection...")
    
    # Don't retry if initial connection failed (configuration issue)
    # This prevents infinite retry loops when REDIS_URL is wrong
    if _redis_connection_failed:
        return None
    
    # Validate REDIS_URL is configured
    if not REDIS_URL:
        logger.error("[REDIS] REDIS_URL not configured. Set Variables: REDIS_URL=${{api.REDIS_URL}}")
        _redis_connection_failed = True
        return None
    
    # Attempt connection
    try:
        client = redis.from_url(
            REDIS_URL,
            decode_responses=True,      # Auto-decode bytes to str
            socket_connect_timeout=5    # 5s timeout for connection
        )
        client.ping()  # Verify connection works
        
        # Track first successful connection (for logging)
        is_first_connection = not _redis_connection_attempted
        _redis_connection_attempted = True
        
        # Cache for future calls
        _redis_client_cache = client
        
        # Log only on first connection (avoid spam on reconnections)
        if is_first_connection:
            logger.info("[REDIS] Connected successfully")
        
        return client
    except (RedisError, ValueError, OSError) as e:
        # Log only on initial failure (avoid spam on reconnection failures)
        if not _redis_connection_attempted:
            error_msg = str(e)[:200]
            logger.error(f"[REDIS] Initial connection failed: {error_msg}")
            logger.error(f"[REDIS] REDIS_URL format: redis://user:pass@host:port")
            logger.error(f"[REDIS] Set Variables: REDIS_URL=${{{{api.REDIS_URL}}}}")
            _redis_connection_failed = True
        # For reconnection failures, silently return None (will retry on next call)
        return None


def enqueue_job(job_id: str, article_id: str, inputs: dict) -> bool:
    """Add a job to the Redis queue for worker processing.
    
    Queue structure (FIFO):
        [oldest ← ... ← newest]
         ↑ BLPOP        ↑ RPUSH
         (Worker)       (API)
    
    Flow:
        1. API calls this function when user requests article generation
        2. Job data is serialized to JSON and pushed to queue
        3. Worker picks up job with BLPOP (blocking pop from left)
        4. First-in, first-out order ensures fair processing
    
    Args:
        job_id: Unique job identifier (UUID)
        article_id: Associated article ID
        inputs: Job parameters (language, level, length, topic)
        
    Returns:
        True if enqueued successfully, False if Redis unavailable
    """
    client = get_redis_client()
    if not client:
        # Error already logged in get_redis_client (only once)
        return False
    
    # Prepare job data for queue
    job_data = {
        'job_id': job_id,
        'article_id': article_id,
        'inputs': inputs,
        'created_at': datetime.now().isoformat()
    }
    
    try:
        # RPUSH: Add to right end of list (newest jobs go to the right)
        # Combined with BLPOP (pop from left), this ensures FIFO order
        # Example: RPUSH "opad:jobs" '{"job_id": "123", ...}'
        client.rpush(QUEUE_NAME, json.dumps(job_data))
        logger.info("Job enqueued successfully", extra={"jobId": job_id, "articleId": article_id})
        return True
    except RedisError as e:
        logger.error("Failed to enqueue job", extra={"jobId": job_id, "articleId": article_id, "error": str(e)})
        return False


def dequeue_job() -> Optional[dict]:
    """Remove and return the oldest job from the Redis queue (blocking).
    
    Queue structure (FIFO):
        [oldest ← ... ← newest]
         ↑ BLPOP        ↑ RPUSH
         (Worker)       (API)
    
    Blocking behavior:
        - If queue has jobs: returns immediately with oldest job
        - If queue is empty: waits up to 1 second for a job
        - This prevents busy-waiting (CPU waste) while staying responsive
    
    Flow:
        1. Worker calls this function in a loop
        2. BLPOP waits for a job (blocks up to 1 second)
        3. When job arrives, returns job data
        4. Worker processes job, then calls this again
    
    Returns:
        Job data dict {'job_id', 'article_id', 'inputs', 'created_at'}
        or None if queue is empty or Redis unavailable
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        # BLPOP: Blocking pop from left end of list (oldest jobs)
        # timeout=1: Wait up to 1 second for a job
        # Returns: (queue_name, job_data_json) or None if timeout
        # Example: BLPOP "opad:jobs" 1
        result = client.blpop(QUEUE_NAME, timeout=1)
        if result:
            _, job_data_str = result  # Unpack (queue_name, data)
            return json.loads(job_data_str)
        return None  # Timeout (queue was empty for 1 second)
    except (RedisError, json.JSONDecodeError) as e:
        # Don't log every dequeue failure (worker polls continuously)
        # Initial connection errors already logged in get_redis_client
        return None


def get_job_status(job_id: str) -> Optional[dict]:
    """Retrieve current job status from Redis.
    
    Status data structure:
        {
            'id': 'job-uuid',
            'article_id': 'article-uuid',
            'status': 'queued' | 'running' | 'succeeded' | 'failed',
            'progress': 0-100,
            'message': 'Current task description',
            'error': 'Error message if failed',
            'created_at': 'ISO timestamp',
            'updated_at': 'ISO timestamp'
        }
    
    Status lifecycle:
        queued → running → succeeded/failed
        
    TTL: 24 hours (auto-deleted after)
    
    Args:
        job_id: Job identifier (UUID)
        
    Returns:
        Job status dict or None if not found/expired
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        status_key = f'opad:job:{job_id}'
        status_data = client.get(status_key)  # GET key
        if status_data:
            return json.loads(status_data)
        return None  # Job not found or expired
    except (RedisError, json.JSONDecodeError) as e:
        # Don't log every status check failure (clients poll frequently)
        # Initial connection errors already logged in get_redis_client
        return None


def update_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    message: Optional[str] = None,
    error: Optional[str] = None,
    article_id: Optional[str] = None
) -> bool:
    """Update job status in Redis with field preservation logic.
    
    Field preservation rules:
        - article_id: Use provided, or preserve existing
        - created_at: Preserve existing, or set new if status='queued'
        - progress: Preserve existing if new value is 0 and existing > 0
          (prevents progress reset on error: 95% -> 0%)
    
    Why preserve fields?
        - Multiple callers update status (API, Worker, progress.py)
        - Not all callers have all fields (e.g., Worker doesn't know created_at)
        - Prevents data loss from partial updates
    
    Status lifecycle:
        queued (API) → running (Worker) → succeeded/failed (Worker)
                                      ↑
                                   progress updates (progress.py)
    
    Args:
        job_id: Job identifier (UUID)
        status: Job status ('queued', 'running', 'succeeded', 'failed')
        progress: Progress percentage (0-100)
        message: User-facing status message
        error: Error message if status='failed'
        article_id: Associated article ID (optional, preserved if not provided)
        
    Returns:
        True if updated successfully, False if Redis unavailable
    """
    client = get_redis_client()
    if not client:
        return False
    
    status_key = f'opad:job:{job_id}'
    
    # Read existing status to preserve fields
    existing_article_id = None
    existing_created_at = None
    existing_progress = None
    try:
        existing_data = client.get(status_key)
        if existing_data:
            existing_status = json.loads(existing_data)
            existing_article_id = existing_status.get('article_id')
            existing_created_at = existing_status.get('created_at')
            existing_progress = existing_status.get('progress')
    except (RedisError, json.JSONDecodeError, KeyError):
        # If we can't read existing data, continue with provided values
        pass
    
    # Apply field preservation rules
    
    # Rule 1: article_id - use provided or preserve existing
    final_article_id = article_id if article_id is not None else existing_article_id
    
    # Rule 2: created_at - preserve existing, or set new for 'queued' status
    final_created_at = existing_created_at
    if final_created_at is None and status == 'queued':
        final_created_at = datetime.now().isoformat()
    
    # Rule 3: progress - preserve existing if new is 0 and existing is higher
    # This prevents error handlers from resetting progress (e.g., 95% -> 0%)
    final_progress = progress
    if progress == 0 and existing_progress and existing_progress > 0:
        final_progress = existing_progress
    
    # Build status data
    status_data = {
        'id': job_id,
        'status': status,
        'progress': final_progress,
        'message': message or '',
        'error': error,
        'updated_at': datetime.now().isoformat()
    }
    
    # Add optional fields if available
    if final_article_id:
        status_data['article_id'] = final_article_id
    
    if final_created_at:
        status_data['created_at'] = final_created_at
    
    try:
        # SETEX: Set with expiration (24 hours = 86400 seconds)
        # Auto-cleanup prevents Redis from filling up with old jobs
        # Example: SETEX "opad:job:123" 86400 '{"status": "running", ...}'
        client.setex(status_key, 86400, json.dumps(status_data))
        extra_data = {"jobId": job_id, "status": status, "progress": final_progress}
        if article_id or existing_article_id:
            extra_data["articleId"] = article_id or existing_article_id
        logger.debug("Updated job status", extra=extra_data)
        return True
    except RedisError as e:
        # Don't log every update failure (called frequently during job execution)
        # Initial connection errors already logged in get_redis_client
        return False

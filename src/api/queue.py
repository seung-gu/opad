"""Redis queue management for job processing."""

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
QUEUE_NAME = 'opad:jobs'

# Cache connection - single attempt only
_redis_client_cache = None
_redis_connection_attempted = False
_redis_connection_failed = False


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client connection.
    
    Attempts connection ONCE per deployment. If it fails, logs error once and stops.
    
    Returns:
        Redis client or None if connection fails
    """
    global _redis_client_cache, _redis_connection_attempted, _redis_connection_failed
    
    # If already failed, return None immediately (no log)
    if _redis_connection_failed:
        return None
    
    # Return cached client if available
    if _redis_client_cache:
        try:
            _redis_client_cache.ping()
            return _redis_client_cache
        except:
            # Cache is stale, clear it
            _redis_client_cache = None
    
    # If already attempted and failed, don't retry
    if _redis_connection_attempted:
        return None
    
    # Mark as attempted
    _redis_connection_attempted = True
    
    if not REDIS_URL:
        logger.error("[REDIS] REDIS_URL not configured. Set Variables: REDIS_URL=${{api.REDIS_URL}}")
        _redis_connection_failed = True
        return None
    
    # Reject localhost URLs
    if 'localhost' in REDIS_URL or '127.0.0.1' in REDIS_URL:
        logger.error(f"[REDIS] Invalid URL contains localhost. Use ${{{{api.REDIS_URL}}}} in Railway Variables.")
        _redis_connection_failed = True
        return None
    
    try:
        client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        client.ping()
        # Cache successful connection
        _redis_client_cache = client
        logger.info("[REDIS] Connected successfully")
        return client
    except (RedisError, ValueError, OSError) as e:
        # Log error ONCE and mark as failed
        error_msg = str(e)[:150]
        if "localhost" in error_msg or "127.0.0.1" in error_msg:
            logger.error(f"[REDIS] Connection to localhost failed.")
        elif "Name or service not known" in error_msg:
            logger.error(f"[REDIS] DNS resolution failed. Set Variables: REDIS_URL=${{{{api.REDIS_URL}}}}")
        else:
            logger.error(f"[REDIS] Connection failed: {error_msg}")
        logger.error("[REDIS] Will not retry. Fix Variables and redeploy.")
        _redis_connection_failed = True
        return None


def enqueue_job(job_id: str, article_id: str, inputs: dict) -> bool:
    """Enqueue a job to Redis queue.
    
    Args:
        job_id: Unique job identifier
        article_id: Associated article ID
        inputs: Job inputs (language, level, length, topic)
        
    Returns:
        True if enqueued successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        # Error already logged in get_redis_client (only once)
        return False
    
    job_data = {
        'job_id': job_id,
        'article_id': article_id,
        'inputs': inputs,
        'created_at': datetime.now().isoformat()
    }
    
    try:
        # Add to queue (left push for FIFO)
        client.lpush(QUEUE_NAME, json.dumps(job_data))
        logger.info(f"Job {job_id} enqueued successfully")
        return True
    except RedisError as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        return False


def dequeue_job() -> Optional[dict]:
    """Dequeue a job from Redis queue (blocking).
    
    Returns:
        Job data dictionary or None if queue is empty/error
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        # Blocking right pop (waits for job, timeout=1 second)
        result = client.brpop(QUEUE_NAME, timeout=1)
        if result:
            _, job_data_str = result
            return json.loads(job_data_str)
        return None
    except (RedisError, json.JSONDecodeError) as e:
        # Don't log every dequeue failure (worker polls continuously)
        # Error already logged in get_redis_client
        return None


def get_job_status(job_id: str) -> Optional[dict]:
    """Get job status from Redis.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status dictionary or None if not found
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        status_key = f'opad:job:{job_id}'
        status_data = client.get(status_key)
        if status_data:
            return json.loads(status_data)
        return None
    except (RedisError, json.JSONDecodeError) as e:
        # Don't log every status check failure (API polls frequently)
        # Error already logged in get_redis_client
        return None


def update_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    message: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """Update job status in Redis.
    
    Args:
        job_id: Job identifier
        status: Job status (queued, running, succeeded, failed)
        progress: Progress percentage (0-100)
        message: Status message
        error: Error message if failed
        
    Returns:
        True if updated successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    status_key = f'opad:job:{job_id}'
    status_data = {
        'id': job_id,
        'status': status,
        'progress': progress,
        'message': message or '',
        'error': error,
        'updated_at': datetime.now().isoformat()
    }
    
    try:
        # Set with expiration (24 hours)
        client.setex(status_key, 86400, json.dumps(status_data))
        logger.debug(f"Updated job {job_id} status: {status} - {progress}%")
        return True
    except RedisError as e:
        # Don't log every update failure (called frequently)
        # Error already logged in get_redis_client
        return False

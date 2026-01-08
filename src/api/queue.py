"""Redis queue management for job processing."""

import json
import logging
import os
from typing import Optional
from datetime import datetime
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', '')
REDIS_HOST = os.getenv('REDISHOST', '')
REDIS_PORT = os.getenv('REDISPORT', '6379')
REDIS_PASSWORD = os.getenv('REDISPASSWORD', '')
REDIS_USER = os.getenv('REDISUSER', 'default')
QUEUE_NAME = 'opad:jobs'

# Cache connection and track retry count
_redis_client_cache = None
_redis_retry_count = 0
_redis_max_retries = 10  # Log error only after 10 failed attempts

# Construct Redis URL from individual variables if URL is incomplete
# Railway provides incomplete URL (missing host), so we need to construct it
if REDIS_URL and '@:' in REDIS_URL:
    # URL is missing host (e.g., redis://user:pass@:6379)
    if REDIS_HOST:
        # Use REDISHOST if provided (should be set when Private Networking is enabled)
        REDIS_URL = REDIS_URL.replace('@:', f'@{REDIS_HOST}:')
    else:
        # REDISHOST is empty - this means Private Networking is not configured
        # For API service: should use Private Network (${{ Redis.REDIS_URL }})
        # For Worker service: should use Public Network URL
        logger.error(f"[REDIS] REDISHOST is empty - Private Networking may not be enabled")
        logger.error(f"[REDIS] For API: Use ${{ Redis.REDIS_URL }} in Variables")
        logger.error(f"[REDIS] For Worker: Use Public Network URL in Variables")
        # Don't auto-fix, let it fail with clear error
elif not REDIS_URL and REDIS_PASSWORD:
    # No URL provided, can't construct without REDISHOST
    if REDIS_HOST:
        REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    else:
        logger.error(f"[REDIS] Cannot build URL: missing both REDIS_URL and REDISHOST")

if not REDIS_URL:
    logger.error("[REDIS] Cannot construct Redis URL: missing required variables")


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client connection.
    
    Uses Railway-provided REDIS_URL or constructs from individual variables.
    Connection is cached - if it fails once, it won't retry to avoid log spam.
    
    Returns:
        Redis client or None if connection fails
    """
    global _redis_client_cache, _redis_retry_count
    
    # Return cached client if available
    if _redis_client_cache:
        try:
            _redis_client_cache.ping()
            return _redis_client_cache
        except:
            # Cache is stale, clear it
            _redis_client_cache = None
    
    if not REDIS_URL:
        _redis_retry_count += 1
        if _redis_retry_count == _redis_max_retries:
            logger.error("[REDIS] REDIS_URL not configured after 10 attempts. Check Railway Variables.")
        return None
    
    # Reject localhost URLs
    if 'localhost' in REDIS_URL or '127.0.0.1' in REDIS_URL:
        _redis_retry_count += 1
        if _redis_retry_count == _redis_max_retries:
            logger.error(f"[REDIS] Invalid URL contains localhost after 10 attempts. Use ${{{{ Redis.REDIS_URL }}}}.")
        return None
    
    try:
        client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        client.ping()
        # Cache successful connection and reset retry count
        _redis_client_cache = client
        _redis_retry_count = 0
        return client
    except (RedisError, ValueError, OSError) as e:
        # Increment retry count and log only at threshold
        _redis_retry_count += 1
        if _redis_retry_count == _redis_max_retries:
            error_msg = str(e)[:150]
            if "localhost" in error_msg or "127.0.0.1" in error_msg:
                logger.error(f"[REDIS] Connection to localhost failed after 10 attempts. Configure ${{{{ Redis.REDIS_URL }}}}.")
            elif "Name or service not known" in error_msg:
                logger.error(f"[REDIS] DNS failed after 10 attempts. Check Variables: ${{{{ Redis.REDIS_URL }}}} for API, Public URL for Worker.")
            else:
                logger.error(f"[REDIS] Connection failed after 10 attempts: {error_msg}")
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

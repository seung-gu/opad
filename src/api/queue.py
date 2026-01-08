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
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
REDIS_HOST = os.getenv('REDISHOST', '')
REDIS_PORT = os.getenv('REDISPORT', '6379')
REDIS_PASSWORD = os.getenv('REDISPASSWORD', '')
REDIS_USER = os.getenv('REDISUSER', 'default')
QUEUE_NAME = 'opad:jobs'

# Log all Redis variables for debugging
logger.info(f"REDIS_URL: {REDIS_URL}")
logger.info(f"REDISHOST: {REDIS_HOST}")
logger.info(f"REDISPORT: {REDIS_PORT}")
logger.info(f"REDISPASSWORD: {REDIS_PASSWORD[:10]}..." if REDIS_PASSWORD else "REDISPASSWORD: empty")
logger.info(f"REDISUSER: {REDIS_USER}")

# If host is missing in URL, construct from individual variables
if REDIS_URL and '@:' in REDIS_URL:
    if REDIS_HOST:
        # Use REDISHOST if available
        REDIS_URL = REDIS_URL.replace('@:', f'@{REDIS_HOST}:')
        logger.info(f"Fixed Redis URL using REDISHOST: {REDIS_URL}")
    elif REDIS_PASSWORD and REDIS_PORT:
        # Construct URL from individual variables
        # Railway Redis add-on might need explicit construction
        REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@redis:{REDIS_PORT}"
        logger.warning(f"Constructed Redis URL from individual variables: {REDIS_URL}")
    else:
        logger.error("Cannot construct Redis URL: missing REDISHOST or REDISPASSWORD")
        logger.error("Please check Railway Redis service Variables")

if not REDIS_URL or REDIS_URL == 'redis://localhost:6379':
    logger.warning("REDIS_URL not set or using default. Make sure Redis add-on is connected in Railway.")


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client connection.
    
    Returns:
        Redis client or None if connection fails
    """
    try:
        # Parse Redis URL (Railway provides REDIS_URL)
        client = redis.from_url(REDIS_URL, decode_responses=True)
        # Test connection
        client.ping()
        return client
    except (RedisError, ValueError) as e:
        logger.error(f"Failed to connect to Redis at {REDIS_URL}: {e}")
        logger.error("Make sure Redis add-on is connected and REDIS_URL environment variable is set.")
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
        logger.error("Redis client not available")
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
        logger.error(f"Failed to dequeue job: {e}")
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
        logger.error(f"Failed to get job status {job_id}: {e}")
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
        logger.error(f"Failed to update job status {job_id}: {e}")
        return False

"""Redis implementation of JobQueuePort.

Manages the job queue system using Redis:
- Queue: FIFO list of pending jobs (RPUSH + BLPOP)
- Status: Individual job status tracking with 24h TTL
- Connection: Cached client with automatic reconnection
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import redis
from redis.exceptions import RedisError

from domain.model.job import JobContext

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', '')
QUEUE_NAME = 'opad:jobs'


class RedisJobQueueAdapter:
    def __init__(self):
        self._client_cache: Optional[redis.Redis] = None
        self._connection_attempted: bool = False
        self._connection_failed: bool = False

    def _get_client(self) -> Optional[redis.Redis]:
        """Get Redis client with caching and reconnection logic."""
        if self._client_cache:
            try:
                self._client_cache.ping()
                return self._client_cache
            except Exception:
                self._client_cache = None
                logger.debug("[REDIS] Cached client failed ping, attempting reconnection...")

        if self._connection_failed:
            return None

        if not REDIS_URL:
            logger.error("[REDIS] REDIS_URL not configured. Set Variables: REDIS_URL=${api.REDIS_URL}")
            self._connection_failed = True
            return None

        try:
            client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            client.ping()

            is_first = not self._connection_attempted
            self._connection_attempted = True
            self._client_cache = client

            if is_first:
                logger.info("[REDIS] Connected successfully")

            return client
        except (RedisError, ValueError, OSError) as e:
            if not self._connection_attempted:
                error_msg = str(e)[:200]
                logger.error(f"[REDIS] Initial connection failed: {error_msg}")
                logger.error("[REDIS] REDIS_URL format: redis://user:pass@host:port")
                self._connection_failed = True
            return None

    # ── JobQueuePort implementation ──────────────────────────

    def enqueue(self, job_id: str, article_id: str, inputs: dict, user_id: str | None = None) -> bool:
        client = self._get_client()
        if not client:
            return False

        job_data = {
            'job_id': job_id,
            'article_id': article_id,
            'user_id': user_id,
            'inputs': inputs,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        try:
            client.rpush(QUEUE_NAME, json.dumps(job_data))
            logger.info("Job enqueued successfully", extra={"jobId": job_id, "articleId": article_id})
            return True
        except RedisError as e:
            logger.error("Failed to enqueue job", extra={"jobId": job_id, "articleId": article_id, "error": str(e)})
            return False

    def dequeue(self, timeout: int = 1) -> JobContext | None:
        client = self._get_client()
        if not client:
            logger.debug("[DEQUEUE] Redis client unavailable, cannot dequeue job")
            return None

        try:
            result = client.blpop(QUEUE_NAME, timeout=timeout)
            if result:
                _, job_data_str = result
                job_data = json.loads(job_data_str)
                ctx = JobContext.from_dict(job_data)
                if ctx:
                    logger.debug("[DEQUEUE] Successfully dequeued job", extra=ctx.log_extra)
                return ctx
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning("[DEQUEUE] Failed to dequeue job", extra={"error": str(e), "errorType": type(e).__name__})
            return None

    def get_status(self, job_id: str) -> dict | None:
        client = self._get_client()
        if not client:
            return None

        try:
            status_key = f'opad:job:{job_id}'
            status_data = client.get(status_key)
            if status_data:
                return json.loads(status_data)
            return None
        except (RedisError, json.JSONDecodeError):
            return None

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: int = 0,
        message: str = '',
        error: str | None = None,
        article_id: str | None = None,
    ) -> bool:
        client = self._get_client()
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
            pass

        final_article_id = article_id if article_id is not None else existing_article_id

        final_created_at = existing_created_at
        if final_created_at is None and status == 'queued':
            final_created_at = datetime.now(timezone.utc).isoformat()

        final_progress = progress
        if progress == 0 and existing_progress and existing_progress > 0:
            final_progress = existing_progress

        status_data = {
            'id': job_id,
            'status': status,
            'progress': final_progress,
            'message': message or '',
            'error': error,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

        if final_article_id:
            status_data['article_id'] = final_article_id
        if final_created_at:
            status_data['created_at'] = final_created_at

        try:
            client.setex(status_key, 86400, json.dumps(status_data))
            logger.debug("Updated job status", extra={"jobId": job_id, "status": status, "progress": final_progress})
            return True
        except RedisError:
            return False

    def get_stats(self) -> dict | None:
        client = self._get_client()
        if not client:
            return None

        stats = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'total': 0,
        }

        try:
            cursor = 0
            pattern = 'opad:job:*'

            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    try:
                        status_data = client.get(key)
                        if status_data:
                            job_data = json.loads(status_data)
                            s = job_data.get('status', 'unknown')
                            if s in stats:
                                stats[s] += 1
                            stats['total'] += 1
                    except (json.JSONDecodeError, KeyError):
                        continue

                if cursor == 0:
                    break

            logger.info("Job statistics retrieved", extra={
                "totalJobs": stats['total'],
                "queued": stats['queued'],
                "running": stats['running'],
                "completed": stats['completed'],
                "failed": stats['failed'],
            })

            return stats
        except RedisError as e:
            logger.error("Failed to get job stats", extra={"error": str(e)})
            return None

    def ping(self) -> bool:
        client = self._get_client()
        if not client:
            return False
        try:
            client.ping()
            return True
        except Exception:
            return False

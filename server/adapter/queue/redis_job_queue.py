"""Redis implementation of JobQueuePort.

Manages the job queue system using Redis:
- Queue: FIFO list of pending jobs (RPUSH + BLPOP)
- Status: Individual job status tracking with 24h TTL
- Connection: Cached client with automatic reconnection
"""

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import redis
from redis.exceptions import RedisError

from dataclasses import asdict
from domain.model.article import Article
from domain.model.job import JobContext
from domain.model.errors import QueueUnavailableError

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', '')
QUEUE_NAME = 'opad:jobs'


class RedisJobQueueAdapter:
    def __init__(self):
        self._client_cache: Optional[redis.Redis] = None

    def _get_client(self) -> Optional[redis.Redis]:
        """Get Redis client with caching and reconnection logic."""
        if self._client_cache:
            return self._client_cache

        if not REDIS_URL:
            logger.error("[REDIS] REDIS_URL not configured. Set Variables: REDIS_URL=${api.REDIS_URL}")
            return None

        try:
            client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            client.ping()
            self._client_cache = client

            logger.info("[REDIS] Connected successfully")
            return client
        except (RedisError, ValueError, OSError) as e:
            logger.warning(f"[REDIS] Connection failed: {str(e)[:200]}")
            return None

    # ── JobQueuePort implementation ──────────────────────────

    def enqueue(self, article: Article) -> bool:
        client = self._get_client()
        if not client:
            return False

        job_data = {
            'job_id': article.job_id,
            'article_id': article.id,
            'user_id': article.user_id,
            'inputs': asdict(article.inputs),
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        try:
            client.rpush(QUEUE_NAME, json.dumps(job_data))
            logger.info("Job enqueued successfully", extra={"jobId": article.job_id, "articleId": article.id})
            return True
        except RedisError:
            logger.exception("Failed to enqueue job", extra={"jobId": article.job_id, "articleId": article.id})
            return False

    def dequeue(self, timeout: int = 1) -> JobContext | None:
        """Pop the next job, blocking up to `timeout` seconds.

        Returns:
            JobContext if a job was popped, None if the queue was empty.

        Raises:
            QueueUnavailableError: Redis is unreachable. Distinct from an
                empty queue (None) — callers must not treat it as idle.
        """
        client = self._get_client()
        if not client:
            raise QueueUnavailableError("Redis client unavailable")

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
        except RedisError as e:
            self._client_cache = None
            raise QueueUnavailableError("Redis connection lost during dequeue") from e
        except json.JSONDecodeError as e:
            logger.warning("[DEQUEUE] Corrupted job data, discarding", extra={"error": str(e)})
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

        try:
            status_values = self._scan_all_job_status_values(client)
            stats = self._tally(status_values)
            logger.info("Job statistics retrieved", extra={"totalJobs": stats['total']})
            return stats
        except RedisError:
            logger.exception("Failed to get job stats")
            return None

    @staticmethod
    def _scan_all_job_status_values(client) -> list[str]:
        """Scan all job keys and return their status strings."""
        result = []
        for key in client.scan_iter(match='opad:job:*', count=100):
            try:
                raw = client.get(key)
                if raw:
                    result.append(json.loads(raw).get('status', 'unknown'))
            except (json.JSONDecodeError, KeyError):
                continue
        return result

    @staticmethod
    def _tally(status_values: list[str]) -> dict:
        """Count job statuses."""
        counts = Counter(status_values)
        return {
            'queued': counts.get('queued', 0),
            'running': counts.get('running', 0),
            'completed': counts.get('completed', 0),
            'failed': counts.get('failed', 0),
            'total': len(status_values),
        }

    def ping(self) -> bool:
        client = self._get_client()
        if not client:
            return False
        try:
            client.ping()
            return True
        except Exception:
            return False

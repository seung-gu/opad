"""Job processing context and utilities."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from api.job_queue import update_job_status
from utils.mongodb import update_article_status

logger = logging.getLogger(__name__)


@dataclass
class JobContext:
    """Context object for job processing, managing state and common operations."""

    job_id: str
    article_id: str | None
    user_id: str | None
    inputs: dict
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, job_data: dict) -> 'JobContext | None':
        """Create JobContext from queue data. Returns None if invalid."""
        job_id = job_data.get('job_id')
        inputs = job_data.get('inputs', {})

        if not job_id or not inputs:
            logger.error(f"Invalid job data: {job_data}")
            return None

        return cls(
            job_id=job_id,
            article_id=job_data.get('article_id'),
            user_id=job_data.get('user_id'),
            inputs=inputs
        )

    @property
    def log_extra(self) -> dict:
        """Common extra fields for structured logging."""
        return {"jobId": self.job_id, "articleId": self.article_id}

    def update_status(self, status: str, progress: int, message: str, error: str = None):
        """Update job status in Redis."""
        update_job_status(self.job_id, status, progress, message, error, self.article_id)

    def mark_failed(self, message: str, error: str = None):
        """Mark both job and article as failed."""
        self.update_status('failed', 0, message, error)
        if self.article_id:
            update_article_status(self.article_id, 'failed')


def translate_error(error: Exception) -> str:
    """Translate technical error to user-friendly message."""
    msg = str(error).lower()
    if "json" in msg:
        return "AI model returned invalid response. Please try again."
    if "timeout" in msg:
        return "Request timed out. Please try again."
    if "rate limit" in msg or "429" in msg:
        return "Rate limit exceeded. Please wait and try again."
    return f"Job failed: {type(error).__name__}"

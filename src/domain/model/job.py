"""Job domain model — typed container for queue job data."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from domain.model.article import ArticleInputs

logger = logging.getLogger(__name__)


@dataclass
class JobContext:
    """Typed container for job queue data. Parses and validates raw dict once."""

    job_id: str
    article_id: str | None
    user_id: str | None
    inputs: ArticleInputs
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, job_data: dict) -> 'JobContext | None':
        """Create JobContext from queue data. Returns None if invalid."""
        job_id = job_data.get('job_id')
        raw_inputs = job_data.get('inputs', {})

        if not job_id or not raw_inputs:
            logger.error(f"Invalid job data: {job_data}")
            return None

        return cls(
            job_id=job_id,
            article_id=job_data.get('article_id'),
            user_id=job_data.get('user_id'),
            inputs=ArticleInputs(
                language=raw_inputs.get('language', ''),
                level=raw_inputs.get('level', ''),
                length=raw_inputs.get('length', ''),
                topic=raw_inputs.get('topic', ''),
            ),
        )

    @property
    def log_extra(self) -> dict:
        """Common extra fields for structured logging."""
        return {"jobId": self.job_id, "articleId": self.article_id}

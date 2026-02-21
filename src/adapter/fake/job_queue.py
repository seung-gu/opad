"""In-memory implementation of JobQueuePort for testing."""

from collections import deque
from datetime import datetime, timezone

from domain.model.article import ArticleInputs
from domain.model.job import JobContext


class FakeJobQueueAdapter:
    def __init__(self):
        self.queue: deque[JobContext] = deque()
        self.statuses: dict[str, dict] = {}

    def enqueue(self, job_id: str, article_id: str, inputs: dict, user_id: str | None = None) -> bool:
        self.queue.append(JobContext(
            job_id=job_id,
            article_id=article_id,
            user_id=user_id,
            inputs=ArticleInputs(
                language=inputs.get('language', ''),
                level=inputs.get('level', ''),
                length=inputs.get('length', ''),
                topic=inputs.get('topic', ''),
            ),
        ))
        return True

    def dequeue(self, timeout: int = 1) -> JobContext | None:
        if self.queue:
            return self.queue.popleft()
        return None

    def get_status(self, job_id: str) -> dict | None:
        return self.statuses.get(job_id)

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: int = 0,
        message: str = '',
        error: str | None = None,
        article_id: str | None = None,
    ) -> bool:
        existing = self.statuses.get(job_id, {})

        final_article_id = article_id if article_id is not None else existing.get('article_id')
        final_created_at = existing.get('created_at')
        if final_created_at is None and status == 'queued':
            final_created_at = datetime.now(timezone.utc).isoformat()

        final_progress = progress
        if progress == 0 and existing.get('progress', 0) > 0:
            final_progress = existing['progress']

        self.statuses[job_id] = {
            'id': job_id,
            'status': status,
            'progress': final_progress,
            'message': message or '',
            'error': error,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'article_id': final_article_id,
            'created_at': final_created_at,
        }
        return True

    def get_stats(self) -> dict | None:
        stats = {'queued': 0, 'running': 0, 'completed': 0, 'failed': 0, 'total': 0}
        for s in self.statuses.values():
            status = s.get('status', 'unknown')
            if status in stats:
                stats[status] += 1
            stats['total'] += 1
        return stats

    def ping(self) -> bool:
        return True

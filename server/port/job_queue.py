"""Port definition for JobQueue."""

from typing import Protocol

from domain.model.article import Article
from domain.model.job import JobContext


class JobQueuePort(Protocol):
    def enqueue(self, article: Article) -> bool: ...
    def dequeue(self, timeout: int = 1) -> JobContext | None: ...
    def get_status(self, job_id: str) -> dict | None: ...
    def update_status(
        self,
        job_id: str,
        status: str,
        progress: int = 0,
        message: str = '',
        error: str | None = None,
        article_id: str | None = None,
    ) -> bool: ...
    def get_stats(self) -> dict | None: ...
    def ping(self) -> bool: ...

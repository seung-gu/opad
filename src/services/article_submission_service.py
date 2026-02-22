"""Article submission service — handles article creation and queue submission.

API-side flow: duplicate check → create → enqueue
"""

import logging

from domain.model.article import Article, ArticleInputs, ArticleStatus
from domain.model.errors import DuplicateArticleError, EnqueueError, DomainError
from port.article_repository import ArticleRepository
from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)


def submit_generation(
    inputs: ArticleInputs,
    user_id: str,
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    force: bool = False,
) -> Article:
    """Submit article generation request.

    Returns the created Article (with job_id set).
    Raises DuplicateArticleError or EnqueueError on failure.
    """
    logger.info("Article generation requested", extra={
        "userId": user_id,
        "topic": inputs.topic,
        "language": inputs.language
    })

    _check_duplicate(repo, job_queue, inputs, force, user_id)

    article = Article.create(inputs, user_id)

    if not repo.save(article):
        raise DomainError("Failed to save article to repository")

    logger.info("Article created", extra={"articleId": article.id, "jobId": article.job_id})

    _enqueue_job(job_queue, repo, article)

    return article


def _check_duplicate(
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    inputs: ArticleInputs,
    force: bool,
    user_id: str | None,
) -> None:
    """Raise DuplicateArticleError if a matching article exists."""
    if force:
        return

    existing = repo.find_duplicate(inputs, user_id, hours=24)
    if not existing:
        return

    job_data = None
    if existing.job_id:
        job_data = job_queue.get_status(existing.job_id)

    raise DuplicateArticleError(existing.id, job_data)


def _enqueue_job(
    job_queue: JobQueuePort,
    repo: ArticleRepository,
    article: Article,
) -> None:
    """Enqueue job or raise EnqueueError."""
    if not job_queue.update_status(
        article.job_id, 'queued', 0,
        'Job queued, waiting for worker...',
        article_id=article.id,
    ):
        raise EnqueueError("Failed to initialize job status")

    if not job_queue.enqueue(article):
        job_queue.update_status(
            article.job_id, 'failed', 0,
            'Failed to enqueue job', 'Queue service unavailable',
            article_id=article.id,
        )
        repo.update_status(article.id, ArticleStatus.FAILED)
        raise EnqueueError("Failed to enqueue job")

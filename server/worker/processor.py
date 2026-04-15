"""Job processor - Worker service core logic.

Architecture:
    JobQueuePort -> dequeue() -> process_job() -> generate_article() -> ArticleRepository
                                      |
                              JobQueuePort.update_status()
"""

import logging
from collections.abc import Callable

from domain.model.article import ArticleStatus
from domain.model.job import JobContext
from port.article_repository import ArticleRepository
from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)


def _translate_error(error: Exception) -> str:
    """Translate technical error to user-friendly message."""
    msg = str(error).lower()
    if "json" in msg:
        return "AI model returned invalid response. Please try again."
    if "timeout" in msg:
        return "Request timed out. Please try again."
    if "rate limit" in msg or "429" in msg:
        return "Rate limit exceeded. Please wait and try again."
    return f"Job failed: {type(error).__name__}"


def process_job(
    ctx: JobContext,
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    generate: Callable[..., bool] | None = None,
) -> bool:
    """Process a single job from the queue."""

    def mark_failed(message: str, error: str | None = None):
        job_queue.update_status(ctx.job_id, 'failed', 0, message, error, ctx.article_id)
        if ctx.article_id:
            repo.update_status(ctx.article_id, ArticleStatus.FAILED)

    logger.info("Processing job", extra=ctx.log_extra)
    job_queue.update_status(ctx.job_id, 'running', 0, 'Starting article generation...', article_id=ctx.article_id)

    try:
        if not generate:
            mark_failed('Internal configuration error', 'generate function is None')
            return False

        article = repo.get_by_id(ctx.article_id) if ctx.article_id else None
        if not article:
            mark_failed('Article not found', f'Article {ctx.article_id} not found in database')
            return False

        success = generate(article=article, user_id=ctx.user_id, inputs=ctx.inputs, job_id=ctx.job_id)

        if success:
            job_queue.update_status(ctx.job_id, 'completed', 100, 'Article generated successfully!', article_id=ctx.article_id)
            logger.info("Job completed", extra=ctx.log_extra)
        else:
            mark_failed('Failed to generate or save article', 'Generation returned False')

        return success

    except Exception as e:
        logger.error(f"Job failed: {e}", extra={**ctx.log_extra, "error": str(e)})
        mark_failed(_translate_error(e), f"{type(e).__name__}: {str(e)[:200]}")
        return False


def run_worker_loop(
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    generate: Callable[..., bool],
):
    """Main worker loop - continuously processes jobs from queue."""
    logger.info("Worker started, waiting for jobs...")

    while True:
        try:
            ctx = job_queue.dequeue()

            if ctx:
                logger.info("Received job", extra=ctx.log_extra)
                process_job(ctx, repo, job_queue, generate)
            else:
                import time
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            import time
            time.sleep(5)

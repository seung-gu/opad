"""Job processor - Worker service core logic.

This module contains the worker's main processing logic:
1. Dequeue jobs from Redis queue (FIFO order)
2. Execute CrewAI to generate articles
3. Save results to MongoDB
4. Update job status in Redis

Architecture:
    Redis Queue -> dequeue_job() -> process_job() -> CrewAI -> MongoDB
                                        |
                                  update_job_status() -> Redis Status

Progress Tracking:
    JobProgressListener subscribes to CrewAI events for real-time task updates.

Token Usage:
    After execution, token usage is retrieved via CrewAI's built-in metrics
    (agent.llm.get_token_usage_summary()) and saved to MongoDB per agent/model.
"""

import logging
import sys
from pathlib import Path

_src_path = Path(__file__).parent.parent
sys.path.insert(0, str(_src_path))

from crew.main import run as run_crew
from api.job_queue import dequeue_job
from utils.mongodb import get_user_vocabulary_for_generation
from utils.token_usage import save_crew_token_usage
from worker.context import JobContext, translate_error
from crew.progress_listener import JobProgressListener
from crew.models import ReviewedArticle
from port.article_repository import ArticleRepository
from domain.model.article import ArticleStatus


logger = logging.getLogger(__name__)


def process_job(job_data: dict, repo: ArticleRepository) -> bool:
    """Process a single job from the queue.

    Args:
        job_data: Job data from queue (job_id, article_id, user_id, inputs, created_at)
        repo: ArticleRepository (injected from main.py or test)

    Returns:
        True if job completed, False if failed
    """
    ctx = JobContext.from_dict(job_data, repo)
    if not ctx:
        return False

    logger.info("Processing job", extra=ctx.log_extra)
    ctx.update_status('running', 0, 'Starting CrewAI execution...')

    try:
        from crewai.events.event_bus import crewai_event_bus

        with crewai_event_bus.scoped_handlers():
            # Listener registers event handlers in __init__ for real-time progress updates.
            # It subscribes to CrewAI events and updates Redis with job progress.
            listener = JobProgressListener(
                job_id=ctx.job_id,
                article_id=ctx.article_id or ""
            )

            # Fetch vocabulary for personalized generation (always set default to avoid template error)
            # Filter by target level to avoid vocab too difficult for the article
            vocab = None
            if ctx.user_id and ctx.inputs.get('language'):
                vocab = get_user_vocabulary_for_generation(
                    user_id=ctx.user_id,
                    language=ctx.inputs['language'],
                    target_level=ctx.inputs.get('level'),
                    limit=50
                )
            ctx.inputs['vocabulary_list'] = vocab if vocab else ""

            # Execute CrewAI
            logger.info("Executing CrewAI", extra=ctx.log_extra)
            result = run_crew(inputs=ctx.inputs)
            logger.info("CrewAI completed", extra=ctx.log_extra)

            # Save token usage for each agent (even if task failed - tokens were still consumed)
            if ctx.user_id:
                save_crew_token_usage(result, ctx.user_id, ctx.article_id, ctx.job_id)

            # Check for task failures
            if listener.task_failed:
                logger.warning("Task failed during execution", extra=ctx.log_extra)
                if ctx.article_id:
                    repo.update_status(ctx.article_id, ArticleStatus.FAILED)
                return False

        # Log replaced sentences from review
        reviewed = result.pydantic
        if isinstance(reviewed, ReviewedArticle) and reviewed.replaced_sentences:
            for change in reviewed.replaced_sentences:
                logger.info(
                    f"Sentence replaced: '{change.original}' -> '{change.replaced}' ({change.rationale})",
                    extra=ctx.log_extra
                )

        # Save to MongoDB
        logger.info("Saving article", extra=ctx.log_extra)
        content = reviewed.article_content
        if not repo.save_content(ctx.article_id, content, ctx.started_at):
            ctx.mark_failed('Failed to save article to database', 'MongoDB save error')
            return False

        # Mark completed
        ctx.update_status('completed', 100, 'Article generated successfully!')
        logger.info("Job completed", extra=ctx.log_extra)
        return True

    except Exception as e:
        logger.error(f"Job failed: {e}", extra={**ctx.log_extra, "error": str(e)})
        ctx.mark_failed(translate_error(e), f"{type(e).__name__}: {str(e)[:200]}")
        return False


def run_worker_loop(repo: ArticleRepository):
    """Main worker loop - continuously processes jobs from Redis queue."""
    logger.info("Worker started, waiting for jobs...")

    while True:
        try:
            job_data = dequeue_job()

            if job_data:
                job_id = job_data.get('job_id')
                logger.info("Received job", extra={"jobId": job_id})
                process_job(job_data, repo)
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

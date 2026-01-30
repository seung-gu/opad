"""Job tracking coordinator for CrewAI article generation.

This module provides a unified JobTracker class that coordinates:
1. JobProgressListener - Real-time task progress updates via CrewAI events
2. ArticleGenerationTokenTracker - LLM token usage tracking via LiteLLM callbacks

The JobTracker implements the context manager protocol for automatic setup and
cleanup of tracking infrastructure.

Architecture:
    with JobTracker(job_id, user_id, article_id) as tracker:
        result = run_crew(inputs)
        # tracker.listener available for checking task_failed status

Usage:
    from crewai.events.event_bus import crewai_event_bus

    with crewai_event_bus.scoped_handlers():
        with JobTracker(ctx.job_id, ctx.user_id, ctx.article_id) as tracker:
            result = run_crew(inputs=ctx.inputs)
            if tracker.listener.task_failed:
                # Handle failure
"""

import logging
from types import TracebackType
from typing import Self

import litellm

from crew.progress_listener import JobProgressListener
from worker.token_tracker import ArticleGenerationTokenTracker

logger = logging.getLogger(__name__)


class JobTracker:
    """Coordinator for job progress and token tracking during article generation.

    This class unifies JobProgressListener and ArticleGenerationTokenTracker into
    a single context manager that handles setup and cleanup automatically.

    Attributes:
        job_id: The job ID being tracked.
        user_id: The user ID who initiated the job (optional, for token tracking).
        article_id: The article ID being generated.
        listener: The JobProgressListener instance (created on __enter__).
        token_tracker: The ArticleGenerationTokenTracker instance (if user_id exists).

    Example:
        with crewai_event_bus.scoped_handlers():
            with JobTracker(job_id, user_id, article_id) as tracker:
                result = run_crew(inputs)
                if tracker.listener.task_failed:
                    handle_failure()
    """

    def __init__(
        self,
        job_id: str,
        user_id: str | None,
        article_id: str | None
    ) -> None:
        """Initialize the JobTracker.

        Args:
            job_id: Job ID to track in Redis.
            user_id: User ID for token tracking (None for anonymous users).
            article_id: Article ID being generated.
        """
        self.job_id = job_id
        self.user_id = user_id
        self.article_id = article_id

        # These are created in __enter__
        self.listener: JobProgressListener | None = None
        self.token_tracker: ArticleGenerationTokenTracker | None = None
        self._original_callbacks: list = []  # Saved for restoration on exit

    def __enter__(self) -> Self:
        """Set up tracking infrastructure.

        Creates:
        1. JobProgressListener for CrewAI task progress events
        2. ArticleGenerationTokenTracker for LLM token usage (if user_id exists)

        Returns:
            Self for use in context manager.
        """
        # Create progress listener (always)
        self.listener = JobProgressListener(
            job_id=self.job_id,
            article_id=self.article_id or ""
        )

        # Create token tracker only for authenticated users
        if self.user_id:
            self.token_tracker = ArticleGenerationTokenTracker(
                job_id=self.job_id,
                user_id=self.user_id,
                article_id=self.article_id
            )
            # Save original callbacks for restoration on exit
            self._original_callbacks = litellm.callbacks.copy() if litellm.callbacks else []
            litellm.callbacks = [self.token_tracker]
            logger.debug(
                "Token tracking enabled",
                extra={"jobId": self.job_id, "userId": self.user_id}
            )

        logger.debug(
            "JobTracker initialized",
            extra={
                "jobId": self.job_id,
                "userId": self.user_id,
                "articleId": self.article_id,
                "tokenTrackingEnabled": self.token_tracker is not None
            }
        )

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        """Clean up tracking infrastructure.

        Clears LiteLLM callbacks to prevent memory leaks and interference
        with other jobs.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Traceback if an exception was raised.
        """
        # Restore original LiteLLM callbacks
        if self.token_tracker is not None:
            litellm.callbacks = self._original_callbacks
            logger.debug(
                "Token tracking cleanup completed",
                extra={"jobId": self.job_id}
            )

        logger.debug(
            "JobTracker cleanup completed",
            extra={"jobId": self.job_id}
        )

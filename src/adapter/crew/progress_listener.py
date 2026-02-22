"""Event listener for tracking job progress via CrewAI events.

This module implements a custom event listener that monitors CrewAI task execution
and updates job status in real-time via JobQueuePort (no direct Redis dependency).
"""

import logging
from typing import TYPE_CHECKING

from crewai.events.base_event_listener import BaseEventListener
from crewai.events.types.task_events import (
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
)

if TYPE_CHECKING:
    from crewai.events.event_bus import CrewAIEventsBus
    from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)

# Task progress mapping (4 CrewAI tasks + uploading = 0-100%)
TASK_PROGRESS = {
    'find_news_articles': {'start': 0, 'end': 25, 'label': 'Finding news articles'},
    'pick_best_article': {'start': 25, 'end': 50, 'label': 'Selecting best article'},
    'adapt_news_article': {'start': 50, 'end': 75, 'label': 'Adapting article for learners'},
    'review_article_quality': {'start': 75, 'end': 95, 'label': 'Reviewing article quality'},
    'uploading': {'start': 95, 'end': 100, 'label': 'Uploading to DB'},
}


class JobProgressListener(BaseEventListener):
    """Event listener for tracking CrewAI task progress.

    Uses JobQueuePort for status updates instead of importing Redis directly.
    Must be used within crewai_event_bus.scoped_handlers() context.
    """

    def __init__(self, job_id: str, article_id: str, job_queue: 'JobQueuePort'):
        self.job_id = job_id
        self.article_id = article_id
        self.job_queue = job_queue
        self.task_failed = False

        self.task_progress = TASK_PROGRESS

        super().__init__()

        logger.info("JobProgressListener initialized", extra={"jobId": job_id, "articleId": article_id})

    def setup_listeners(self, crewai_event_bus: 'CrewAIEventsBus') -> None:
        """Setup event listeners on the CrewAI event bus."""

        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_started(source, event: TaskStartedEvent):
            task_name = event.task.name if event.task else None

            if task_name and task_name in self.task_progress:
                info = self.task_progress[task_name]

                self.job_queue.update_status(
                    job_id=self.job_id,
                    status='running',
                    progress=info['start'],
                    message=f"Starting: {info['label']}",
                    article_id=self.article_id,
                )

                logger.info(
                    f"[EVENT] Task started: {task_name} "
                    f"({info['start']}% - {info['label']})"
                )
            else:
                task_desc = event.task.description if event.task else None
                desc_preview = task_desc[:50] if task_desc else 'None'
                logger.warning(
                    f"[EVENT] Unknown task started. Name: '{task_name}', "
                    f"Description: '{desc_preview}...' (truncated)"
                )

        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source, event: TaskCompletedEvent):
            task_name = event.task.name if event.task else None

            if task_name and task_name in self.task_progress:
                info = self.task_progress[task_name]

                self.job_queue.update_status(
                    job_id=self.job_id,
                    status='running',
                    progress=info['end'],
                    message=f"Completed: {info['label']}",
                    article_id=self.article_id,
                )

                logger.info(
                    f"[EVENT] Task completed: {task_name} "
                    f"({info['end']}% - {info['label']})"
                )
            else:
                task_desc = event.task.description if event.task else None
                desc_preview = task_desc[:50] if task_desc else 'None'
                logger.warning(
                    f"[EVENT] Unknown task completed. Name: '{task_name}', "
                    f"Description: '{desc_preview}...' (truncated)"
                )

        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_failed(source, event: TaskFailedEvent):
            task_name = event.task.name if event.task else None
            task_label = self.task_progress.get(task_name, {}).get('label', task_name) if task_name else 'Unknown task'
            error_msg = event.error if hasattr(event, 'error') else 'Unknown error'

            self.task_failed = True

            logger.error(
                f"[EVENT] Task failed: {task_name} ({task_label}) - Error: {error_msg}"
            )

            current_progress = 0
            if task_name and task_name in self.task_progress:
                current_progress = self.task_progress[task_name]['start']

            self.job_queue.update_status(
                job_id=self.job_id,
                status='failed',
                progress=current_progress,
                message=f"Task failed: {task_label}",
                error=str(error_msg)[:200],
                article_id=self.article_id,
            )

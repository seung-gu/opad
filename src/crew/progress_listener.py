"""Event listener for tracking job progress via CrewAI events.

This module implements a custom event listener that monitors CrewAI task execution
and updates Redis job status in real-time.

Key Concepts:
- BaseEventListener: Abstract base class for creating custom event listeners
- CrewAIEventsBus: Global singleton event bus that manages event registration
- TaskStartedEvent/TaskCompletedEvent: Events emitted by CrewAI during task execution

How it works:
1. JobProgressListener inherits from BaseEventListener
2. When instantiated, __init__ automatically calls setup_listeners()
3. setup_listeners() registers event handlers on the global event bus
4. When CrewAI executes tasks, it emits events to the bus
5. The bus notifies all registered listeners (our handlers)
6. Handlers update Redis with real-time progress

References:
- Official docs: https://docs.crewai.com/concepts/event-listener
- Event types: crewai.events.types.task_events
"""

import logging
from typing import TYPE_CHECKING

from crewai.events.base_event_listener import BaseEventListener
from crewai.events.types.task_events import (
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent
)

if TYPE_CHECKING:
    from crewai.events.event_bus import CrewAIEventsBus

logger = logging.getLogger(__name__)


class JobProgressListener(BaseEventListener):
    """Event listener for tracking CrewAI task progress and updating Redis.
    
    This listener subscribes to CrewAI task events (start/complete/fail) and
    updates the corresponding job status in Redis with accurate progress percentages.
    
    Architecture:
    - Inherits from BaseEventListener (CrewAI's base class)
    - Registers event handlers using @crewai_event_bus.on() decorator syntax
    - Handlers are called automatically by CrewAI when events occur
    - Each handler updates Redis via update_job_status()
    - IMPORTANT: Must be used within crewai_event_bus.scoped_handlers() context
    
    Task Progress Mapping:
    - find_news_articles: 0% → 25%
    - pick_best_article: 25% → 50%
    - adapt_news_article: 50% → 75%
    - add_vocabulary: 75% → 95%
    - R2 upload: 95% → 100% (handled separately in processor.py)
    
    Usage (within scoped_handlers for proper isolation):
        from crewai.events.event_bus import crewai_event_bus
        
        with crewai_event_bus.scoped_handlers():
            listener = JobProgressListener(job_id="abc123", article_id="xyz789")
            crew = ReadingMaterialCreator().crew()
            result = crew.kickoff(inputs=inputs)
            # ✅ Progress updates happen automatically during kickoff()
        # ✅ Handlers are automatically cleared after scoped_handlers exit
    
    Why scoped_handlers is critical:
    - Event handlers registered within the scope are automatically cleared on exit
    - This prevents old handlers from triggering for new jobs
    - Eliminates cross-job state corruption
    
    Args:
        job_id: Job ID to track in Redis
        article_id: Associated article ID
    """
    
    def __init__(self, job_id: str, article_id: str):
        """Initialize the listener and register event handlers.
        
        Note: super().__init__() automatically calls setup_listeners(),
        which registers our handlers using the @event_bus.on() decorator.
        
        Args:
            job_id: Job ID to track
            article_id: Associated article ID
        """
        self.job_id = job_id
        self.article_id = article_id
        self.task_failed = False  # Track if any task failed
        
        # Import shared task progress mapping from utils
        from utils.progress import TASK_PROGRESS
        self.task_progress = TASK_PROGRESS
        
        # ✅ Call parent __init__ AFTER setting instance variables
        # This calls setup_listeners() which needs self.job_id, etc.
        super().__init__()
        
        logger.info("JobProgressListener initialized", extra={"jobId": job_id, "articleId": article_id})
    
    def setup_listeners(self, crewai_event_bus: 'CrewAIEventsBus') -> None:
        """Setup event listeners on the CrewAI event bus.
        
        This method is called automatically by BaseEventListener.__init__().
        It registers handlers for task events using the @event_bus.on() decorator syntax.
        
        Event Flow:
        1. CrewAI starts a task → emits TaskStartedEvent
        2. Event bus receives event → notifies all registered listeners
        3. Our on_task_started() handler is called
        4. Handler updates Redis with task start progress
        5. Same flow for TaskCompletedEvent and TaskFailedEvent
        
        Handler Isolation:
        - Handlers are registered within crewai_event_bus.scoped_handlers() context
        - When the scope exits, all handlers are automatically cleared
        - This prevents cross-job state corruption from lingering handlers
        
        Args:
            crewai_event_bus: Global singleton event bus (injected by parent class)
        """
        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_started(source, event: TaskStartedEvent):
            """Handler called when CrewAI starts a task.
            
            Event Data:
            - event.task: Task object with name, description, agent, etc.
            - event.context: Task context (previous task outputs)
            
            Args:
                source: Event source (usually the Crew instance)
                event: TaskStartedEvent with task details
            """
            # Get task name (not description!) from Task object
            # Task name matches the method name in crew.py and TASK_PROGRESS keys
            # Example: 'find_news_articles', 'pick_best_article', etc.
            task_name = event.task.name if event.task else None
            
            if task_name and task_name in self.task_progress:
                info = self.task_progress[task_name]
                
                # Import here to avoid circular dependency
                from api.queue import update_job_status
                
                update_job_status(
                    job_id=self.job_id,
                    status='running',
                    progress=info['start'],  # ✅ Real-time start progress!
                    message=f"Starting: {info['label']}",
                    article_id=self.article_id
                )
                
                logger.info(
                    f"[EVENT] Task started: {task_name} "
                    f"({info['start']}% - {info['label']})"
                )
            else:
                # Unknown task - log warning with both name and description for debugging
                task_desc = event.task.description if event.task else None
                desc_preview = task_desc[:50] if task_desc else 'None'
                logger.warning(
                    f"[EVENT] Unknown task started. Name: '{task_name}', "
                    f"Description: '{desc_preview}...' (truncated)"
                )
        
        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source, event: TaskCompletedEvent):
            """Handler called when CrewAI completes a task.
            
            Event Data:
            - event.task: Task object with name, description, etc.
            - event.output: TaskOutput with raw/pydantic/json_dict results
            
            Args:
                source: Event source
                event: TaskCompletedEvent with task and output
            """
            # Get task name (not description!) from Task object
            task_name = event.task.name if event.task else None
            
            if task_name and task_name in self.task_progress:
                info = self.task_progress[task_name]
                
                from api.queue import update_job_status
                
                update_job_status(
                    job_id=self.job_id,
                    status='running',
                    progress=info['end'],  # ✅ Real-time completion progress!
                    message=f"Completed: {info['label']}",
                    article_id=self.article_id
                )
                
                logger.info(
                    f"[EVENT] Task completed: {task_name} "
                    f"({info['end']}% - {info['label']})"
                )
            else:
                # Unknown task - log warning with both name and description for debugging
                task_desc = event.task.description if event.task else None
                desc_preview = task_desc[:50] if task_desc else 'None'
                logger.warning(
                    f"[EVENT] Unknown task completed. Name: '{task_name}', "
                    f"Description: '{desc_preview}...' (truncated)"
                )
        
        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_failed(source, event: TaskFailedEvent):
            """Handler called when a task fails.
            
            Event Data:
            - event.task: Task object with name, description, etc.
            - event.error: Error message
            
            Args:
                source: Event source
                event: TaskFailedEvent with error details
            """
            # Get task name (not description!) from Task object
            task_name = event.task.name if event.task else None
            task_label = self.task_progress.get(task_name, {}).get('label', task_name) if task_name else 'Unknown task'
            error_msg = event.error if hasattr(event, 'error') else 'Unknown error'
            
            # Mark that a task has failed
            self.task_failed = True
            
            logger.error(
                f"[EVENT] Task failed: {task_name} ({task_label}) - Error: {error_msg}"
            )
            
            # Update job status to failed
            from api.queue import update_job_status
            
            # Get current progress if task is known
            current_progress = 0
            if task_name and task_name in self.task_progress:
                current_progress = self.task_progress[task_name]['start']
            
            update_job_status(
                job_id=self.job_id,
                status='failed',
                progress=current_progress,  # Preserve progress at failure point
                message=f"Task failed: {task_label}",
                error=str(error_msg)[:200],  # Truncate long errors
                article_id=self.article_id
            )

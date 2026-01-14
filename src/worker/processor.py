"""Job processor - Worker service core logic.

This module contains the worker's main processing logic:
1. Dequeue jobs from Redis queue (FIFO order)
2. Execute CrewAI to generate articles
3. Upload results to Cloudflare R2
4. Update job status in Redis

Architecture:
    Redis Queue → dequeue_job() → process_job() → CrewAI → R2 Upload
                                        ↓
                                  update_job_status() → Redis Status
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
# processor.py is at /app/src/worker/processor.py
# src is at /app/src, so we go up 2 levels
_src_path = Path(__file__).parent.parent
sys.path.insert(0, str(_src_path))

from crew.main import run as run_crew

# Import from src
from api.queue import update_job_status, dequeue_job
from utils.mongodb import save_article

logger = logging.getLogger(__name__)


def process_job(job_data: dict) -> bool:
    """Process a single job from the queue.
    
    Processing flow:
        1. Extract job parameters (job_id, article_id, inputs)
        2. Update status to 'running' (progress=0)
        3. Create JobProgressListener for real-time progress tracking
        4. Execute CrewAI (calls crew.main.run_crew)
           - CrewAI generates article content
           - Progress updates happen automatically via JobProgressListener
        5. Upload result to Cloudflare R2 (progress=95)
        6. Update status to 'succeeded' (progress=100)
        7. Handle success/failure
    
    Progress tracking:
        - JobProgressListener catches CrewAI events and updates Redis in real-time
        - Worker handles initial 'running', R2 upload progress, and final 'succeeded'/'failed' states
        - Event-based tracking provides accurate progress (not estimated)
    
    Error handling:
        - Translates technical errors to user-friendly messages
        - Preserves progress on failure (e.g., 95% stays 95%, not reset to 0%)
        - Logs detailed error for debugging
        - R2 upload failures don't fail the entire job (content is still generated)
    
    Args:
        job_data: Job data from queue
            {
                'job_id': 'uuid',
                'article_id': 'uuid',
                'inputs': {'language', 'level', 'length', 'topic'},
                'created_at': 'ISO timestamp'
            }
        
    Returns:
        True if job succeeded, False if failed
    """
    job_id = job_data.get('job_id')
    article_id = job_data.get('article_id')
    inputs = job_data.get('inputs', {})
    
    # Validate required fields
    if not job_id or not inputs:
        logger.error(f"Invalid job data: {job_data}")
        return False
    
    logger.info("Processing job", extra={"jobId": job_id, "articleId": article_id})
    
    # Update status to 'running' (initial state)
    update_job_status(
        job_id=job_id,
        status='running',
        progress=0,
        message='Starting CrewAI execution...',
        article_id=article_id
    )
    
    try:
        # ✅ Create JobProgressListener for real-time progress tracking
        # Use CrewAI's scoped_handlers() to ensure handlers are isolated per job
        # This prevents cross-job state corruption from lingering handlers
        from crew.progress_listener import JobProgressListener
        from crewai.events.event_bus import crewai_event_bus
        
        # Use scoped_handlers() to create an isolated event handler scope for this job
        # All handlers registered within this scope are automatically cleared when exiting
        with crewai_event_bus.scoped_handlers():
            # Create listener - handlers will be registered in the current scope
            listener = JobProgressListener(job_id=job_id, article_id=article_id)
            logger.info("Event listener registered", extra={"jobId": job_id})
            
            # ✅ Execute CrewAI
            # During execution, CrewAI emits TaskStartedEvent/TaskCompletedEvent
            # Our progress_listener automatically catches these events and updates Redis
            logger.info("Executing CrewAI", extra={"jobId": job_id})
            result = run_crew(inputs=inputs)
            
            logger.info("CrewAI execution completed", extra={"jobId": job_id})
            
            # ✅ Check if any task failed during execution
            # If TaskFailedEvent was emitted, listener.task_failed will be True
            # In this case, the job status is already set to 'failed' by the event handler
            # We should not overwrite it with 'succeeded'
            if listener.task_failed:
                logger.warning(
                    "Job had task failures but CrewAI didn't raise exception. Job status already set to 'failed' by event handler.",
                    extra={"jobId": job_id}
                )
                return False
        # ✅ Event handlers are automatically cleared here (scoped_handlers exit)
        
        # ✅ Save to MongoDB
        # CRITICAL: Save is required for article to be accessible to users
        # If save fails, the generated content is lost (only exists in memory)
        # Therefore, save failure = job failure
        logger.info("Saving article to MongoDB", extra={"jobId": job_id, "articleId": article_id})
        try:
            # Save article content to MongoDB
            # Note: Only content and status are updated. Metadata (language, level, length, topic)
            # was set during article creation and remains immutable.
            # result.raw contains markdown text with all information (title, source, url, date, author, body)
            success = save_article(
                article_id=article_id,
                content=result.raw
            )
            if not success:
                raise Exception("Failed to save article to MongoDB")
            logger.info("Successfully saved article to MongoDB", extra={"jobId": job_id, "articleId": article_id})
        except Exception as save_error:
            logger.error("MongoDB save failed", extra={"jobId": job_id, "articleId": article_id, "error": str(save_error)})
            # Save failure means content is lost - mark job as failed
            update_job_status(
                job_id=job_id,
                status='failed',
                progress=0,
                message='Failed to save article to database',
                error=f'MongoDB save error: {str(save_error)[:200]}',
                article_id=article_id
            )
            return False
        
        # ✅ Update final status to 'succeeded'
        if not update_job_status(job_id, 'succeeded', 100, 'Article generated successfully!', article_id=article_id):
            logger.error("Failed to update final status, marking as failed", extra={"jobId": job_id})
            update_job_status(
                job_id, 'failed', 100, 
                'Article saved but status update failed', 
                error='Redis status update failed',
                article_id=article_id
            )
            return False
        
        logger.info("Job completed successfully", extra={"jobId": job_id, "articleId": article_id})
        return True
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Translate technical errors to user-friendly messages
        # This improves UX by hiding implementation details
        if "json" in error_msg.lower() or "JSON" in error_msg:
            user_message = "AI model returned invalid response. This may be a temporary issue. Please try again."
            logger.error("Job failed: JSON parsing error", extra={"jobId": job_id, "articleId": article_id, "error": error_msg, "errorType": "JSONParsingError"})
        elif "timeout" in error_msg.lower():
            user_message = "Request timed out. The AI model may be overloaded. Please try again."
            logger.error("Job failed: Timeout", extra={"jobId": job_id, "articleId": article_id, "error": error_msg, "errorType": "Timeout"})
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            user_message = "Rate limit exceeded. Please wait a moment and try again."
            logger.error("Job failed: Rate limit", extra={"jobId": job_id, "articleId": article_id, "error": error_msg, "errorType": "RateLimit"})
        else:
            user_message = f"Job failed: {error_type}"
            logger.error("Job failed", extra={"jobId": job_id, "articleId": article_id, "error": error_msg, "errorType": error_type})
        
        # Update status to 'failed'
        # Note: progress=0 is passed, but update_job_status will preserve existing progress
        # if it's higher (e.g., 95% from R2 upload failure won't be reset to 0%)
        update_job_status(
            job_id=job_id,
            status='failed',
            progress=0,  # Preserved by update_job_status if existing progress > 0
            message=user_message,
            error=f"{error_type}: {error_msg[:200]}",  # Truncate long errors
            article_id=article_id
        )
        
        return False


def run_worker_loop():
    """Main worker loop - continuously processes jobs from Redis queue.
    
    Loop behavior:
        1. Call dequeue_job() (blocks up to 1 second)
        2. If job received, process it
        3. If no job (timeout), wait 5 seconds
        4. Repeat forever
    
    Why blocking dequeue?
        - Prevents busy-waiting (CPU waste)
        - Stays responsive (1 second timeout)
        - No polling overhead
    
    Error handling:
        - KeyboardInterrupt: Graceful shutdown
        - Other exceptions: Log and continue (don't crash worker)
        - Redis connection failures: Wait 5 seconds before retry
    
    Concurrency:
        - Currently processes one job at a time (sequential)
        - TODO: Issue #8 - Add concurrent job processing (multiple workers or threads)
    
    Example flow:
        [Start] → dequeue_job() → Got job? → Yes → process_job() → [Loop]
                                           ↓ No
                                         Wait 5s → [Loop]
    """
    logger.info("Worker started, waiting for jobs...")
    
    while True:
        try:
            # Dequeue job from Redis (blocking, max 1 second wait)
            # Returns job data or None if queue is empty/timeout
            job_data = dequeue_job()
            
            if job_data:
                job_id = job_data.get('job_id')
                logger.info("Received job", extra={"jobId": job_id})
                process_job(job_data)
            else:
                # Queue is empty or Redis connection failed
                # Wait 5 seconds to prevent busy-waiting
                import time
                time.sleep(5)
                
        except KeyboardInterrupt:
            # Graceful shutdown on Ctrl+C
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            # Catch all other exceptions to prevent worker crash
            # Worker should keep running even if a job fails catastrophically
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            import time
            time.sleep(5)  # Wait before retrying to avoid rapid error loops

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
from typing import Optional
from datetime import datetime

# Add src to path for imports
# processor.py is at /app/src/worker/processor.py
# src is at /app/src, so we go up 2 levels
_src_path = Path(__file__).parent.parent
sys.path.insert(0, str(_src_path))

from opad.crew import ReadingMaterialCreator
from opad.main import run as run_crew

# Import from src
from api.queue import update_job_status, dequeue_job
from utils.cloudflare import upload_to_cloud

logger = logging.getLogger(__name__)


def process_job(job_data: dict) -> bool:
    """Process a single job from the queue.
    
    Processing flow:
        1. Extract job parameters (job_id, article_id, inputs)
        2. Update status to 'running'
        3. Execute CrewAI (calls opad.main.run_crew)
           - CrewAI generates article content
           - Uploads to Cloudflare R2
           - Updates progress via utils.progress
        4. Handle success/failure
    
    Progress tracking:
        - utils.progress.update_status() automatically updates Redis
        - Worker only needs to handle initial 'running' and final 'failed' states
        - Success state is set by run_crew() after R2 upload
    
    Error handling:
        - Translates technical errors to user-friendly messages
        - Preserves progress on failure (e.g., 95% stays 95%, not reset to 0%)
        - Logs detailed error for debugging
    
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
    
    logger.info(f"Processing job {job_id} for article {article_id}")
    
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
        # This automatically registers to CrewAI's global event bus
        from opad.progress_listener import JobProgressListener
        progress_listener = JobProgressListener(
            job_id=job_id,
            article_id=article_id
        )
        logger.info(f"Event listener registered for job {job_id}")
        
        # ✅ Execute CrewAI
        # During execution, CrewAI emits TaskStartedEvent/TaskCompletedEvent
        # Our progress_listener automatically catches these events and updates Redis
        logger.info(f"Executing CrewAI for job {job_id}")
        result = run_crew(inputs=inputs)
        
        logger.info(f"Job {job_id} completed successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Translate technical errors to user-friendly messages
        # This improves UX by hiding implementation details
        if "json" in error_msg.lower() or "JSON" in error_msg:
            user_message = "AI model returned invalid response. This may be a temporary issue. Please try again."
            logger.error(f"Job {job_id} failed: JSON parsing error - {error_msg}")
        elif "timeout" in error_msg.lower():
            user_message = "Request timed out. The AI model may be overloaded. Please try again."
            logger.error(f"Job {job_id} failed: Timeout - {error_msg}")
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            user_message = "Rate limit exceeded. Please wait a moment and try again."
            logger.error(f"Job {job_id} failed: Rate limit - {error_msg}")
        else:
            user_message = f"Job failed: {error_type}"
            logger.error(f"Job {job_id} failed: {error_type} - {error_msg}")
        
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
                logger.info(f"Received job: {job_data.get('job_id')}")
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

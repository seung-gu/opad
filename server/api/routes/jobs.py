"""Job-related API routes."""

import logging
from fastapi import APIRouter, HTTPException, Depends

from api.models import JobResponse
from api.dependencies import get_job_queue
from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    job_queue: JobQueuePort = Depends(get_job_queue),
):
    """Get job status by ID."""
    status_data = job_queue.get_status(job_id)

    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=status_data.get('id', job_id),
        article_id=status_data.get('article_id'),
        status=status_data.get('status', 'unknown'),
        progress=status_data.get('progress', 0),
        message=status_data.get('message'),
        created_at=status_data.get('created_at'),
        updated_at=status_data.get('updated_at'),
        error=status_data.get('error')
    )

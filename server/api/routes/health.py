"""Health check endpoint."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.dependencies import get_job_queue
from adapter.mongodb.connection import get_mongodb_client
from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health(
    job_queue: JobQueuePort = Depends(get_job_queue),
):
    """Health check endpoint with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "services": {}
    }

    overall_healthy = True

    # Check Redis connection via port
    try:
        if job_queue.ping():
            health_status["services"]["redis"] = {
                "status": "healthy",
                "message": "Connection successful"
            }
        else:
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "message": "Connection failed or not configured"
            }
            overall_healthy = False
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "message": f"Connection error: {str(e)[:200]}"
        }
        overall_healthy = False

    # Check MongoDB connection
    try:
        mongo_client = get_mongodb_client()
        if mongo_client:
            mongo_client.admin.command('ping')
            health_status["services"]["mongodb"] = {
                "status": "healthy",
                "message": "Connection successful"
            }
        else:
            health_status["services"]["mongodb"] = {
                "status": "unhealthy",
                "message": "Connection failed or not configured"
            }
            overall_healthy = False
    except Exception as e:
        health_status["services"]["mongodb"] = {
            "status": "unhealthy",
            "message": f"Connection error: {str(e)[:200]}"
        }
        overall_healthy = False

    # Update overall status
    if not overall_healthy:
        health_status["status"] = "degraded"

    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content=health_status,
        status_code=status_code
    )

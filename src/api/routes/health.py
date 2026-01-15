"""Health check endpoint."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import sys
from pathlib import Path

# Add src to path
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.queue import get_redis_client
from utils.mongodb import get_mongodb_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    """Health check endpoint with dependency status.
    
    Checks the health of:
    - API service itself
    - Redis connection (for job queue and status)
    - MongoDB connection (for article storage)
    
    Returns:
        JSON response with overall status and individual service statuses
        - 200: All services healthy
        - 503: One or more services unhealthy
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "services": {}
    }
    
    overall_healthy = True
    
    # Check Redis connection
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
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
    
    # Return appropriate status code
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=health_status,
        status_code=status_code
    )

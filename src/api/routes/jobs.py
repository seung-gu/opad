"""Job-related API routes."""

import logging
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

# Add src to path
# jobs.py is at /app/src/api/routes/jobs.py
# src is at /app/src, so we go up 3 levels
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.models import JobResponse
from api.job_queue import get_job_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status_endpoint(job_id: str):
    """Get job status by ID.
    
    클라이언트가 이 엔드포인트를 폴링하여 작업 진행상황을 확인합니다.
    
    상태 흐름:
    - queued: 큐에 대기 중
    - running: Worker가 처리 중
    - completed: 완료
    - failed: 실패
    """
    status_data = get_job_status(job_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # JobResponse 모델에 맞게 변환
    # Redis에 저장된 데이터 구조에 맞춰 매핑
    return JobResponse(
        id=status_data.get('id', job_id),
        article_id=status_data.get('article_id'),
        status=status_data.get('status', 'unknown'),
        progress=status_data.get('progress', 0),
        message=status_data.get('message'),
        created_at=status_data.get('created_at'),  # ISO string, auto-parsed by Pydantic
        updated_at=status_data.get('updated_at'),  # ISO string, auto-parsed by Pydantic
        error=status_data.get('error')
    )

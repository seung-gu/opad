"""Article-related API routes."""

import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

# Add src to path
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.models import ArticleCreate, ArticleResponse, GenerateRequest, GenerateResponse
from api.queue import enqueue_job, update_job_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])

# In-memory storage (임시 - 나중에 Postgres로 교체)
# TODO: 이슈 #8에서 Postgres로 마이그레이션
_articles_store: dict[str, dict] = {}


@router.post("", response_model=ArticleResponse, status_code=201)
async def create_article(article: ArticleCreate):
    """Create a new article record.
    
    현재는 메모리에만 저장 (임시 구현).
    이슈 #8에서 Postgres로 마이그레이션 예정.
    """
    article_id = str(uuid.uuid4())
    article_data = {
        'id': article_id,
        'language': article.language,
        'level': article.level,
        'length': article.length,
        'topic': article.topic,
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    _articles_store[article_id] = article_data
    logger.info(f"Created article {article_id}")
    
    return ArticleResponse(**article_data)


@router.post("/{article_id}/generate", response_model=GenerateResponse)
async def generate_article(article_id: str, request: GenerateRequest):
    """Generate article by enqueueing a job.
    
    핵심 개념:
    - 즉시 jobId를 반환 (비동기 처리)
    - 실제 CrewAI 실행은 worker가 처리
    - 클라이언트는 jobId로 상태를 폴링
    
    Args:
        article_id: Article ID
        request: Generation parameters
        
    Returns:
        Job ID and article ID for tracking
    """
    # Article 존재 확인
    if article_id not in _articles_store:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Job ID 생성
    job_id = str(uuid.uuid4())
    
    # Job 입력 데이터 준비
    inputs = {
        'language': request.language,
        'level': request.level,
        'length': request.length,
        'topic': request.topic
    }
    
    # Redis 큐에 job enqueue
    success = enqueue_job(job_id, article_id, inputs)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to enqueue job. Queue service unavailable."
        )
    
    # Job 상태 초기화 (queued)
    update_job_status(
        job_id=job_id,
        status='queued',
        progress=0,
        message='Job queued, waiting for worker...'
    )
    
    logger.info(f"Job {job_id} enqueued for article {article_id}")
    
    return GenerateResponse(
        job_id=job_id,
        article_id=article_id,
        message="Article generation started. Use job_id to track progress."
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str):
    """Get article by ID."""
    if article_id not in _articles_store:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return ArticleResponse(**_articles_store[article_id])

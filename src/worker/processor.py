"""Job processor - executes CrewAI and saves results."""

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
    """Process a single job.
    
    이 함수는 worker의 핵심 로직입니다:
    1. Job 데이터에서 입력 파라미터 추출
    2. CrewAI 실행 (기존 opad.main.run 재사용)
    3. 결과를 R2에 업로드
    4. Job 상태 업데이트
    
    Args:
        job_data: Job data from queue (job_id, article_id, inputs, created_at)
        
    Returns:
        True if successful, False otherwise
    """
    job_id = job_data.get('job_id')
    article_id = job_data.get('article_id')
    inputs = job_data.get('inputs', {})
    
    if not job_id or not inputs:
        logger.error(f"Invalid job data: {job_data}")
        return False
    
    logger.info(f"Processing job {job_id} for article {article_id}")
    
    # Set job_id for progress tracking
    from utils.progress import set_current_job_id
    set_current_job_id(job_id)
    
    # Job 상태를 running으로 업데이트
    update_job_status(
        job_id=job_id,
        status='running',
        progress=0,
        message='Starting CrewAI execution...'
    )
    
    try:
        # CrewAI 실행
        # 기존 opad.main.run 함수를 재사용
        # progress.update_status가 자동으로 Redis에도 업데이트함
        
        logger.info(f"Executing CrewAI for job {job_id}")
        result = run_crew(inputs=inputs)
        
        # 결과가 CrewAI의 CrewOutput 객체
        # result.raw는 markdown 문자열
        markdown_content = result.raw if hasattr(result, 'raw') else str(result)
        
        # R2에 업로드
        # TODO: article_id 기반 경로로 변경 (이슈 #8)
        # 현재는 기존 경로 유지
        logger.info(f"Uploading result to R2 for job {job_id}")
        upload_success = upload_to_cloud(markdown_content)
        
        if not upload_success:
            raise Exception("Failed to upload to R2")
        
        # Job 완료 상태 업데이트
        update_job_status(
            job_id=job_id,
            status='succeeded',
            progress=100,
            message='Article generated and uploaded successfully!'
        )
        
        logger.info(f"Job {job_id} completed successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Parse error message for better user feedback
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
        
        # Job 실패 상태 업데이트
        update_job_status(
            job_id=job_id,
            status='failed',
            progress=0,
            message=user_message,
            error=f"{error_type}: {error_msg[:200]}"  # Truncate long errors
        )
        
        return False


def run_worker_loop():
    """Main worker loop - continuously consumes jobs from queue.
    
    이 함수는 worker의 메인 루프입니다:
    - Redis 큐에서 job을 dequeue (blocking)
    - Job을 처리
    - 무한 루프로 계속 대기
    
    개념:
    - Blocking dequeue: 큐가 비어있으면 대기 (CPU 낭비 없음)
    - 한 번에 하나씩 처리 (순차 처리)
    - TODO: 이슈 #8에서 동시성 제어 추가 (여러 job 병렬 처리)
    """
    logger.info("Worker started, waiting for jobs...")
    
    while True:
        try:
            # 큐에서 job 가져오기 (blocking, 최대 1초 대기)
            job_data = dequeue_job()
            
            if job_data:
                logger.info(f"Received job: {job_data.get('job_id')}")
                process_job(job_data)
            else:
                # 큐가 비어있거나 Redis 연결 실패 시 대기
                # Redis 연결 실패 시 무한 루프 방지
                import time
                time.sleep(5)  # 5초 대기
                
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            # 에러가 발생해도 worker는 계속 실행 (다음 job 처리)
            import time
            time.sleep(5)  # 에러 발생 시 5초 대기

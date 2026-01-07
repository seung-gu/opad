"""FastAPI application entry point."""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.routes import articles, jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OPAD API",
    description="API service for OPAD - handles articles and job queue",
    version="0.3.0"
)

# CORS 설정 (Next.js에서 호출 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(articles.router)
app.include_router(jobs.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "OPAD API",
        "version": "0.3.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint.
    
    이슈 #10에서 더 자세한 health check 추가 예정.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    # Railway는 PORT 환경변수를 제공
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

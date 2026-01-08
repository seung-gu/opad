"""FastAPI application entry point."""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
# main.py is at /app/src/api/main.py
# src is at /app/src, so we go up 2 levels
_src_path = Path(__file__).parent.parent
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

# CORS configuration for cross-origin requests from Next.js
# Note: allow_credentials=True requires explicit origin list (not "*")
# Currently credentials are not needed, so we use allow_credentials=False
# For production, set CORS_ORIGINS env var with comma-separated list of allowed origins
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
# Handle wildcard separately: FastAPI expects string "*", not list ["*"]
# Strip whitespace from each origin to handle "origin1, origin2" format
cors_origins = "*" if cors_origins_env == "*" else [origin.strip() for origin in cors_origins_env.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # "*" (string) or ["origin1", "origin2"] (list)
    allow_credentials=False,  # Must be False when using wildcard origins
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

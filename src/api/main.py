"""FastAPI application entry point."""

import os
import sys
import logging
import tomllib
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
# Must be called before importing modules that read env vars (like auth middleware)
load_dotenv()

# Add src to path
# main.py is at /app/src/api/main.py
# src is at /app/src, so we go up 2 levels
_src_path = Path(__file__).parent.parent
sys.path.insert(0, str(_src_path))

from api.routes import articles, jobs, health, endpoints, stats, dictionary, auth, usage
from utils.logging import setup_structured_logging
from utils.mongodb import ensure_indexes

# Set up structured JSON logging
setup_structured_logging()

logger = logging.getLogger(__name__)

# Read version from pyproject.toml (single source of truth)
_project_root = _src_path.parent
with open(_project_root / "pyproject.toml", "rb") as f:
    VERSION = tomllib.load(f)["project"]["version"]

SERVICE_NAME = "One Story A Day API"

# Create FastAPI app
app = FastAPI(
    title=SERVICE_NAME,
    description="API service for One Story A Day - handles articles and job queue",
    version=VERSION
)

# CORS configuration for cross-origin requests from Next.js
# When using JWT authentication with Authorization header:
# - If CORS_ORIGINS="*": allow_credentials must be False (browsers don't support credentials with wildcard)
# - If CORS_ORIGINS is a specific list: allow_credentials can be True
# For production, set CORS_ORIGINS env var with comma-separated list of allowed origins
cors_origins_env = os.getenv("CORS_ORIGINS", "*")

# Parse origins: handle wildcard separately from explicit origin list
# Wildcard "*" is a string, explicit origins become a list
if cors_origins_env == "*":
    cors_origins = "*"
    allow_credentials = False  # Browsers don't support credentials with wildcard
    logger.warning(
        "CORS configured with wildcard origin ('*'). "
        "For production, set CORS_ORIGINS to specific domains (e.g., 'https://app.example.com')"
    )
else:
    # Strip whitespace from each origin to handle "origin1, origin2" format
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    allow_credentials = True  # Can enable credentials with specific origins
    logger.info(f"CORS configured with specific origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # "*" (string) or ["origin1", "origin2"] (list)
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(articles.router)
app.include_router(jobs.router)
app.include_router(health.router)
app.include_router(endpoints.router)
app.include_router(stats.router)
app.include_router(dictionary.router)
app.include_router(auth.router)
app.include_router(usage.router)


@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    # Ensure MongoDB indexes exist
    if ensure_indexes():
        logger.info("MongoDB indexes verified/created successfully")
    else:
        logger.warning("Failed to create MongoDB indexes (MongoDB may be unavailable)")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    # Railway는 PORT 환경변수를 제공
    port = int(os.getenv("PORT", 8000))
    # Disable uvicorn access logs to reduce noise
    # Application logs (via our structured logging) will still be captured
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        access_log=False  # Disable uvicorn's access log (reduces duplicate logs)
    )

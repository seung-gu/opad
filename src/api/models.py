"""Pydantic models for API request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ArticleCreate(BaseModel):
    """Request model for creating an article."""
    language: str = Field(..., description="Target language")
    level: str = Field(..., description="Language level (A1-C2)")
    length: str = Field(..., description="Target word count")
    topic: str = Field(..., description="Article topic")


class ArticleResponse(BaseModel):
    """Response model for article."""
    id: str = Field(..., description="Article ID")
    language: str
    level: str
    length: str
    topic: str
    status: str = Field(..., description="Article status")
    created_at: datetime


class GenerateRequest(BaseModel):
    """Request model for generating article."""
    language: str
    level: str
    length: str
    topic: str


class JobResponse(BaseModel):
    """Response model for job status."""
    id: str = Field(..., description="Job ID")
    article_id: Optional[str] = Field(None, description="Associated article ID")
    status: str = Field(..., description="Job status: queued, running, succeeded, failed")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = Field(None, description="Error message if failed")


class GenerateResponse(BaseModel):
    """Response model for generate endpoint."""
    job_id: str = Field(..., description="Job ID for tracking")
    article_id: str = Field(..., description="Article ID")
    message: str = Field(..., description="Status message")

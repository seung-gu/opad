"""Pydantic models for API request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    """Response model for article."""
    id: str = Field(..., description="Article ID")
    language: str
    level: str
    length: str
    topic: str
    status: str = Field(..., description="Article status")
    created_at: datetime
    owner_id: Optional[str] = Field(None, description="Owner ID for multi-user support")
    job_id: Optional[str] = Field(None, description="Job ID for progress tracking")
    inputs: Optional[dict] = Field(None, description="Structured input parameters")


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
    status: str = Field(..., description="Job status: queued, running, completed, failed")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    # Note: started_at and finished_at are not currently tracked in Redis


class GenerateResponse(BaseModel):
    """Response model for generate endpoint (only returned when generation actually starts)."""
    job_id: str = Field(..., description="Job ID for tracking")
    article_id: str = Field(..., description="Article ID")
    message: str = Field(..., description="Status message")


class ArticleListResponse(BaseModel):
    """Response model for article list with pagination."""
    articles: list[ArticleResponse]
    total: int = Field(..., description="Total number of articles matching filters")
    skip: int = Field(..., description="Number of articles skipped")
    limit: int = Field(..., description="Maximum number of articles returned")


class DefineRequest(BaseModel):
    """Request model for word definition."""
    word: str
    sentence: str
    language: str


class DefineResponse(BaseModel):
    """Response model for word definition."""
    lemma: str
    definition: str
    related_words: Optional[list[str]] = Field(None, description="All words in sentence belonging to this lemma (e.g., for separable verbs)")


class VocabularyRequest(BaseModel):
    """Request model for adding vocabulary."""
    article_id: str = Field(..., description="Article ID")
    word: str = Field(..., description="Original word clicked")
    lemma: str = Field(..., description="Dictionary form (lemma)")
    definition: str = Field(..., description="Word definition")
    sentence: str = Field(..., description="Sentence context")
    language: str = Field(..., description="Language")
    related_words: Optional[list[str]] = Field(None, description="All words in sentence belonging to this lemma")
    span_id: Optional[str] = Field(None, description="Span ID of the clicked word")


class VocabularyResponse(BaseModel):
    """Response model for vocabulary."""
    id: str = Field(..., description="Vocabulary ID")
    article_id: str = Field(..., description="Article ID")
    word: str = Field(..., description="Original word clicked")
    lemma: str = Field(..., description="Dictionary form (lemma)")
    definition: str = Field(..., description="Word definition")
    sentence: str = Field(..., description="Sentence context")
    language: str = Field(..., description="Language")
    related_words: Optional[list[str]] = Field(None, description="All words in sentence belonging to this lemma")
    span_id: Optional[str] = Field(None, description="Span ID of the clicked word")
    created_at: datetime = Field(..., description="Creation timestamp")

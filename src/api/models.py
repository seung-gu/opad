"""Pydantic models for API request/response."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# Type definitions for vocabulary metadata
CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class Conjugations(BaseModel):
    """Verb conjugation forms."""
    present: Optional[str] = None
    past: Optional[str] = None
    perfect: Optional[str] = None

    def __bool__(self) -> bool:
        """Return False if all fields are None."""
        return any(v is not None for v in (self.present, self.past, self.perfect))


class ArticleResponse(BaseModel):
    """Response model for article."""
    id: str = Field(..., description="Article ID")
    language: str
    level: str
    length: str
    topic: str
    status: str = Field(..., description="Article status")
    created_at: datetime
    user_id: Optional[str] = Field(None, description="User ID for multi-user support")
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
    # Note: started_at is not currently tracked in Redis


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


class SearchRequest(BaseModel):
    """Request model for word search."""
    word: str = Field(..., min_length=1, max_length=100, description="Word to search")
    sentence: str = Field(..., min_length=1, max_length=2000, description="Sentence containing the word")
    language: str = Field(..., min_length=2, max_length=50, description="Language of the sentence")


class SearchResponse(BaseModel):
    """Response model for word search."""
    lemma: str
    definition: str
    related_words: Optional[list[str]] = Field(None, description="All words in sentence belonging to this lemma (e.g., for separable verbs)")
    pos: Optional[str] = Field(None, description="Part of speech: noun, verb, adjective, etc.")
    gender: Optional[str] = Field(None, description="Grammatical gender: der/die/das, le/la, el/la")
    conjugations: Optional[Conjugations] = Field(None, description="Verb conjugations by tense")
    level: Optional[CEFRLevel] = Field(None, description="CEFR level (A1-C2)")


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
    pos: Optional[str] = Field(None, description="Part of speech: noun, verb, adjective, etc.")
    gender: Optional[str] = Field(None, description="Grammatical gender: der/die/das, le/la, el/la")
    conjugations: Optional[dict] = Field(None, description="Verb conjugations by tense")
    level: Optional[CEFRLevel] = Field(None, description="CEFR level (A1-C2)")

    @field_validator('conjugations', mode='before')
    @classmethod
    def convert_conjugations(cls, v):
        """Convert Conjugations to dict, return None if empty."""
        if v is None:
            return None
        if isinstance(v, Conjugations):
            return v.model_dump() if v else None
        if isinstance(v, dict):
            return v if any(v.values()) else None
        return v


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
    user_id: Optional[str] = Field(None, description="User ID for multi-user support")
    pos: Optional[str] = Field(None, description="Part of speech: noun, verb, adjective, etc.")
    gender: Optional[str] = Field(None, description="Grammatical gender: der/die/das, le/la, el/la")
    conjugations: Optional[Conjugations] = Field(None, description="Verb conjugations by tense")
    level: Optional[CEFRLevel] = Field(None, description="CEFR level (A1-C2)")


class VocabularyCount(BaseModel):
    """Response model for vocabulary with count (grouped by lemma)."""
    id: str = Field(..., description="Most recent vocabulary ID")
    article_id: str = Field(..., description="Most recent article ID")
    word: str = Field(..., description="Most recent word form")
    lemma: str = Field(..., description="Dictionary form (lemma)")
    definition: str = Field(..., description="Most recent definition")
    sentence: str = Field(..., description="Most recent sentence context")
    language: str = Field(..., description="Language")
    related_words: Optional[list[str]] = Field(None, description="Related words from most recent entry")
    span_id: Optional[str] = Field(None, description="Span ID from most recent entry")
    created_at: datetime = Field(..., description="Most recent entry timestamp")
    user_id: Optional[str] = Field(None, description="User ID")
    count: int = Field(..., description="Number of times this lemma was saved")
    article_ids: list[str] = Field(..., description="Article IDs where this lemma appears")
    pos: Optional[str] = Field(None, description="Part of speech from most recent entry")
    gender: Optional[str] = Field(None, description="Grammatical gender from most recent entry")
    conjugations: Optional[Conjugations] = Field(None, description="Verb conjugations from most recent entry")
    level: Optional[CEFRLevel] = Field(None, description="CEFR level from most recent entry")


class User(BaseModel):
    """User model for authentication."""
    id: str = Field(..., description="User ID (MongoDB _id)")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="Display name")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    provider: str = Field("email", description="Authentication provider")


# Token Usage Models
class OperationUsage(BaseModel):
    """Token usage breakdown by operation type."""
    tokens: int = Field(..., description="Total tokens used for this operation")
    cost: float = Field(..., description="Total cost in USD for this operation")
    count: int = Field(..., description="Number of API calls for this operation")


class DailyUsage(BaseModel):
    """Token usage for a single day."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    tokens: int = Field(..., description="Total tokens used on this day")
    cost: float = Field(..., description="Total cost in USD on this day")


class TokenUsageSummary(BaseModel):
    """Summary of user's token usage over a time period."""
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total estimated cost in USD")
    by_operation: dict[str, OperationUsage] = Field(
        default_factory=dict,
        description="Usage breakdown by operation type (dictionary_search, article_generation)"
    )
    daily_usage: list[DailyUsage] = Field(
        default_factory=list,
        description="Daily usage breakdown sorted by date ascending"
    )


class TokenUsageRecord(BaseModel):
    """Single token usage record."""
    id: str = Field(..., description="Usage record ID")
    user_id: str = Field(..., description="User ID who incurred the usage")
    operation: str = Field(..., description="Operation type: dictionary_search or article_generation")
    model: str = Field(..., description="Model name used")
    prompt_tokens: int = Field(..., description="Number of input tokens")
    completion_tokens: int = Field(..., description="Number of output tokens")
    total_tokens: int = Field(..., description="Total tokens (prompt + completion)")
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Timestamp of the API call")

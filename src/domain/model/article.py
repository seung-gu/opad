# domain/model/article.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ArticleStatus(str, Enum):
    """Enumeration of possible article processing statuses."""
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    DELETED = 'deleted'


@dataclass(frozen=True)
class ArticleInputs:
    """Input parameters for article generation."""
    language: str
    level: str
    length: str
    topic: str


@dataclass
class Article:
    """Domain model representing an article."""
    id: str
    inputs: ArticleInputs
    status: ArticleStatus
    created_at: datetime
    updated_at: datetime

    user_id: str | None = None
    job_id: str | None = None
    content: str | None = None
    started_at: datetime | None = None
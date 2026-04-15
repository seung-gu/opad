# domain/model/article.py

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.model.token_usage import LLMCallResult


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


# ── Value Objects ────────────────────────────────────────


@dataclass(frozen=True)
class SourceInfo:
    """Source metadata from the original news article."""
    title: str
    source_name: str
    source_url: str | None = None
    author: str | None = None
    publication_date: str | None = None


@dataclass(frozen=True)
class EditRecord:
    """Record of a sentence edited during the review process."""
    original: str
    replaced: str
    rationale: str


@dataclass(frozen=True)
class GenerationResult:
    """Article generation result — framework-agnostic domain DTO."""
    content: str
    source: SourceInfo
    edit_history: list[EditRecord]
    agent_usage: list[tuple[str, LLMCallResult]]


# ── Article Domain Model ─────────────────────────────────


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
    source: SourceInfo | None = None
    edit_history: list[EditRecord] = field(default_factory=list)

    # ── factory ───────────────────────────────────────────

    @staticmethod
    def create(inputs: ArticleInputs, user_id: str) -> 'Article':
        """Create a new Article in RUNNING status with generated IDs."""
        now = datetime.now(timezone.utc)
        return Article(
            id=str(uuid.uuid4()),
            inputs=inputs,
            status=ArticleStatus.RUNNING,
            created_at=now,
            updated_at=now,
            user_id=user_id,
            job_id=str(uuid.uuid4()),
        )

    # ── queries ───────────────────────────────────────────

    @property
    def is_deleted(self) -> bool:
        return self.status == ArticleStatus.DELETED

    @property
    def has_content(self) -> bool:
        return self.content is not None and len(self.content) > 0

    def is_owned_by(self, user_id: str) -> bool:
        return self.user_id == user_id

    # ── state transitions ─────────────────────────────────

    def complete(
        self,
        content: str,
        source: SourceInfo | None = None,
        edit_history: list[EditRecord] | None = None,
    ) -> None:
        """Mark article as completed with generated content."""
        self.content = content
        self.status = ArticleStatus.COMPLETED
        self.source = source
        if edit_history is not None:
            self.edit_history = edit_history
        self.updated_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        """Mark article as failed."""
        self.status = ArticleStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        """Soft-delete article."""
        self.status = ArticleStatus.DELETED
        self.updated_at = datetime.now(timezone.utc)


# ── Articles Collection ──────────────────────────────────


@dataclass
class Articles:
    """Collection wrapper for paginated article results."""
    items: list[Article]
    total: int

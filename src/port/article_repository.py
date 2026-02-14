"""Port definition for ArticleRepository."""

from typing import Protocol
from datetime import datetime

from domain.model.article import Article, ArticleInputs, ArticleStatus


class ArticleRepository(Protocol):
    def save_metadata(
        self,
        article_id: str,
        inputs: ArticleInputs,
        status: ArticleStatus = ArticleStatus.RUNNING,
        created_at: datetime | None = None,
        user_id: str | None = None,
        job_id: str | None = None,
    ) -> bool: ...

    def save_content(
        self,
        article_id: str,
        content: str,
        started_at: datetime | None = None,
    ) -> bool: ...

    def get_by_id(self, article_id: str) -> Article | None: ...

    def find_many(
        self,
        skip: int = 0,
        limit: int = 20,
        status: ArticleStatus | None = None,
        language: str | None = None,
        level: str | None = None,
        user_id: str | None = None,
        exclude_deleted: bool = True,
    ) -> tuple[list[Article], int]: ...

    def find_duplicate(
        self,
        inputs: ArticleInputs,
        user_id: str | None = None,
        hours: int = 24,
    ) -> Article | None: ...

    def update_status(self, article_id: str, status: ArticleStatus) -> bool: ...

    def delete(self, article_id: str) -> bool: ...

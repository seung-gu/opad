"""Port definition for ArticleRepository."""

from typing import Protocol

from domain.model.article import Article, ArticleInputs, ArticleStatus, Articles


class ArticleRepository(Protocol):
    def save(self, article: Article) -> bool: ...

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
    ) -> Articles: ...

    def find_duplicate(
        self,
        inputs: ArticleInputs,
        user_id: str | None = None,
        hours: int = 24,
    ) -> Article | None: ...

    def update_status(self, article_id: str, status: ArticleStatus) -> bool: ...

    def delete(self, article_id: str) -> bool: ...

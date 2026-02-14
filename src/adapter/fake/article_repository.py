"""In-memory implementation of ArticleRepository for testing."""

from datetime import datetime, timedelta, timezone

from domain.model.article import Article, ArticleInputs, ArticleStatus


class FakeArticleRepository:
    def __init__(self):
        self.store: dict[str, Article] = {}

    # ── write operations ─────────────────────────────────────

    def save_metadata(
        self,
        article_id: str,
        inputs: ArticleInputs,
        status: ArticleStatus = ArticleStatus.RUNNING,
        created_at: datetime | None = None,
        user_id: str | None = None,
        job_id: str | None = None,
    ) -> bool:
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        self.store[article_id] = Article(
            id=article_id,
            inputs=inputs,
            status=status,
            created_at=created_at,
            updated_at=datetime.now(timezone.utc),
            user_id=user_id,
            job_id=job_id,
        )
        return True

    def save_content(
        self,
        article_id: str,
        content: str,
        started_at: datetime | None = None,
    ) -> bool:
        article = self.store.get(article_id)
        if not article:
            return False

        article.content = content
        article.status = ArticleStatus.COMPLETED
        article.updated_at = datetime.now(timezone.utc)
        if started_at:
            article.started_at = started_at
        return True

    def update_status(self, article_id: str, status: ArticleStatus) -> bool:
        article = self.store.get(article_id)
        if not article:
            return False

        article.status = status
        article.updated_at = datetime.now(timezone.utc)
        return True

    def delete(self, article_id: str) -> bool:
        article = self.store.get(article_id)
        if not article:
            return False

        article.status = ArticleStatus.DELETED
        article.updated_at = datetime.now(timezone.utc)
        return True

    # ── read operations ──────────────────────────────────────

    def get_by_id(self, article_id: str) -> Article | None:
        return self.store.get(article_id)

    def find_many(
        self,
        skip: int = 0,
        limit: int = 20,
        status: ArticleStatus | None = None,
        language: str | None = None,
        level: str | None = None,
        user_id: str | None = None,
        exclude_deleted: bool = True,
    ) -> tuple[list[Article], int]:
        results = list(self.store.values())

        if status:
            results = [a for a in results if a.status == status]
        elif exclude_deleted:
            results = [a for a in results if a.status != ArticleStatus.DELETED]
        if language:
            results = [a for a in results if a.inputs.language == language]
        if level:
            results = [a for a in results if a.inputs.level == level]
        if user_id:
            results = [a for a in results if a.user_id == user_id]

        results.sort(key=lambda a: a.created_at, reverse=True)
        total = len(results)
        return results[skip:skip + limit], total

    def find_duplicate(
        self,
        inputs: ArticleInputs,
        user_id: str | None = None,
        hours: int = 24,
    ) -> Article | None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        for article in sorted(self.store.values(), key=lambda a: a.created_at, reverse=True):
            if article.inputs == inputs and cutoff <= article.created_at and user_id == article.user_id:
                return article
        return None

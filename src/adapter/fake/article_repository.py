"""In-memory implementation of ArticleRepository for testing."""

from datetime import datetime, timedelta, timezone

from domain.model.article import Article, ArticleInputs, ArticleStatus, Articles


class FakeArticleRepository:
    def __init__(self):
        self.store: dict[str, Article] = {}

    # ── write operations ─────────────────────────────────────

    def save(self, article: Article) -> bool:
        self.store[article.id] = article
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
    ) -> Articles:
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
        return Articles(items=results[skip:skip + limit], total=total)

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

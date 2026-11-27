"""In-memory implementation of NewsSource for testing."""

from domain.model.news import NewsArticle


class FakeNewsSource:
    """Fake news source that returns preconfigured search results and pages."""

    def __init__(self, results: list[NewsArticle] | None = None, pages: dict[str, NewsArticle] | None = None):
        self.results = results or []
        self.pages = pages or {}
        self.last_search: tuple[str, str] | None = None
        self.last_fetch: str | None = None

    async def search(self, query: str, language_code: str) -> list[NewsArticle]:
        self.last_search = (query, language_code)
        return self.results

    async def fetch(self, url: str) -> NewsArticle:
        self.last_fetch = url
        return self.pages[url]

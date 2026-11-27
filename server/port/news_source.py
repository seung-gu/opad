"""Port for searching news and fetching one article."""

from typing import Protocol

from domain.model.news import NewsArticle


class NewsSource(Protocol):
    """Outbound port for a news source."""

    async def search(self, query: str, language_code: str) -> list[NewsArticle]:
        """Return recent news articles for the query, without content.

        Errors of the source itself (bad key, outage) are raised as they are.
        """
        ...

    async def fetch(self, url: str) -> NewsArticle:
        """Return the article at the URL with its content.

        Raises ValueError when this page cannot be read (blocked, missing, timed out, no text),
        so the caller can pick another article.
        """
        ...

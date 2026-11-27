"""News search — find candidate articles and read one. No LLM."""

from domain.model.language import get_language
from domain.model.news import NewsArticle
from port.news_source import NewsSource

MIN_WORDS = 200


async def search_news(query: str, language: str, source: NewsSource) -> list[NewsArticle]:
    """Recent news articles for the query in the article language."""
    lang = get_language(language)
    if not lang:
        raise ValueError(f"Unsupported language: {language}")

    found = await source.search(query, lang.code)
    if not found:
        raise ValueError(f"No news articles found for '{query}'. Try a different or broader query.")
    return found


async def fetch_article(url: str, source: NewsSource) -> NewsArticle:
    """The article at the URL with its full text.

    Every failure is a ValueError telling the caller to pick another article: pages the source
    cannot read, and pages under MIN_WORDS words, which also drops video, gallery and podcast pages.
    """
    article = await source.fetch(url)
    words = len((article.content or "").split())
    if words < MIN_WORDS:
        raise ValueError(f"The article at {url} has only {words} words (minimum {MIN_WORDS}). Pick another article.")
    return article

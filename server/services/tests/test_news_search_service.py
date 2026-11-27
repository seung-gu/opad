"""Tests for news_search_service."""

import asyncio

import httpx
import pytest

from adapter.fake.news_source import FakeNewsSource
from domain.model.news import NewsArticle
from services.news_search_service import MIN_WORDS, fetch_article, search_news


def _hit(url: str) -> NewsArticle:
    return NewsArticle(title="t", url=url, source_name="s")


def test_search_uses_language_code():
    source = FakeNewsSource(results=[_hit("https://a.de/news/1")])
    asyncio.run(search_news("Radwege", "German", source))
    assert source.last_search == ("Radwege", "de")


def test_search_with_no_results_raises():
    with pytest.raises(ValueError, match="No news articles found"):
        asyncio.run(search_news("Radwege", "German", FakeNewsSource()))


def test_search_unsupported_language_raises():
    with pytest.raises(ValueError, match="Unsupported language"):
        asyncio.run(search_news("x", "Klingon", FakeNewsSource()))


def test_fetch_returns_article_with_enough_words():
    url = "https://a.de/news/1"
    page = NewsArticle(title="t", url=url, source_name="s", content="Wort " * MIN_WORDS)
    assert asyncio.run(fetch_article(url, FakeNewsSource(pages={url: page}))) == page


def test_fetch_short_article_raises():
    url = "https://a.de/news/1"
    page = NewsArticle(title="t", url=url, source_name="s", content="Wort " * (MIN_WORDS - 1))
    with pytest.raises(ValueError, match=f"only {MIN_WORDS - 1} words"):
        asyncio.run(fetch_article(url, FakeNewsSource(pages={url: page})))


def test_search_keeps_http_errors_as_they_are():
    class _DownSearch(FakeNewsSource):
        async def search(self, query: str, language_code: str) -> list[NewsArticle]:
            raise httpx.ConnectError("down")

    with pytest.raises(httpx.ConnectError):
        asyncio.run(search_news("x", "German", _DownSearch()))

"""Serper news search + article text extraction.

Implements NewsSource: search goes to Serper's news endpoint,
fetch downloads the page and extracts the article text with trafilatura.

API Documentation: https://serper.dev
"""

import asyncio
from urllib.parse import urlparse

import httpx
import trafilatura

from domain.model.news import NewsArticle

SERPER_NEWS_URL = "https://google.serper.dev/news"
TIMEOUT_SECONDS = 15.0
# Some news sites refuse the default httpx user agent
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OPAD/1.0)"}


class SerperNewsSource:
    """News source backed by Serper search and trafilatura extraction.

    search raises httpx errors as they are. fetch turns them into ValueError (see NewsSource.fetch).
    """

    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        self._api_key = api_key
        self._transport = transport  # tests pass httpx.MockTransport

    async def search(self, query: str, language_code: str) -> list[NewsArticle]:
        async with httpx.AsyncClient(transport=self._transport, timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                SERPER_NEWS_URL,
                headers={"X-API-KEY": self._api_key},
                json={"q": query, "hl": language_code},
            )
            response.raise_for_status()

        return [
            NewsArticle(
                title=item["title"],
                url=item["link"],
                source_name=item.get("source") or _host(item["link"]),
                date=item.get("date"),
            )
            for item in response.json().get("news", [])
        ]

    async def fetch(self, url: str) -> NewsArticle:
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=TIMEOUT_SECONDS, follow_redirects=True, headers=FETCH_HEADERS
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Could not open {url} (HTTP {e.response.status_code}). Pick another article.") from e
        except httpx.HTTPError as e:
            raise ValueError(f"Could not open {url} ({type(e).__name__}). Pick another article.") from e

        # httpx decodes by the header charset only. Without one, pass bytes so trafilatura detects it.
        page = response.text if response.charset_encoding else response.content
        # trafilatura is synchronous and parses the whole page
        doc = await asyncio.to_thread(trafilatura.bare_extraction, page, url=url, with_metadata=True)
        if doc is None or not doc.text:
            raise ValueError(f"Could not extract article text from {url}. Pick another article.")

        return NewsArticle(
            title=doc.title or "",
            url=url,
            source_name=doc.sitename or _host(url),
            date=doc.date,
            author=doc.author,
            content=doc.text,
        )


def _host(url: str) -> str:
    return urlparse(url).hostname or url

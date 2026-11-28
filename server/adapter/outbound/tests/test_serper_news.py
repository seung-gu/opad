"""Tests for SerperNewsSource with httpx.MockTransport."""

import asyncio
import json

import httpx
import pytest

from adapter.outbound.serper_news import SERPER_NEWS_URL, SerperNewsSource

BODY = " ".join(["Die Stadt plant neue Radwege entlang des Flusses."] * 40)
ARTICLE_HTML = f"""<html><head>
<title>Neue Radwege in Berlin</title>
<meta property="og:site_name" content="Tagesspiegel">
<meta name="author" content="Anna Schmidt">
<meta property="article:published_time" content="2026-11-20">
</head><body>
<nav>Startseite Politik Sport</nav>
<article><h1>Neue Radwege in Berlin</h1><p>{BODY}</p><p>{BODY}</p></article>
<footer>Impressum Datenschutz</footer>
</body></html>"""


def _source(handler) -> SerperNewsSource:
    return SerperNewsSource("key-123", transport=httpx.MockTransport(handler))


def test_search_sends_query_and_language_and_maps_results():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["X-API-KEY"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "news": [
                    {
                        "title": "Radwege",
                        "link": "https://www.tagesspiegel.de/a",
                        "source": "Tagesspiegel",
                        "date": "2 hours ago",
                    },
                    {"title": "Ohne Quelle", "link": "https://example.org/b"},
                ]
            },
        )

    results = asyncio.run(_source(handler).search("Radwege Berlin", "de"))

    assert seen == {"url": SERPER_NEWS_URL, "key": "key-123", "body": {"q": "Radwege Berlin", "hl": "de"}}
    assert [(r.title, r.url, r.source_name, r.date, r.content) for r in results] == [
        ("Radwege", "https://www.tagesspiegel.de/a", "Tagesspiegel", "2 hours ago", None),
        ("Ohne Quelle", "https://example.org/b", "example.org", None, None),
    ]


def test_search_raises_http_errors():
    source = _source(lambda request: httpx.Response(403))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(source.search("x", "de"))


def test_fetch_extracts_article_text_and_metadata():
    source = _source(lambda request: httpx.Response(200, html=ARTICLE_HTML))

    article = asyncio.run(source.fetch("https://www.tagesspiegel.de/a"))

    assert article.title == "Neue Radwege in Berlin"
    assert article.source_name == "Tagesspiegel"
    assert article.author == "Anna Schmidt"
    assert article.date == "2026-11-20"
    assert "Radwege entlang des Flusses" in article.content
    assert "Impressum" not in article.content


@pytest.mark.parametrize(
    ("content_type", "meta"),
    [
        ("text/html", '<meta charset="iso-8859-15">'),  # charset only in the page
        ("text/html; charset=iso-8859-15", ""),  # charset only in the header
    ],
)
def test_fetch_decodes_a_page_that_is_not_utf8(content_type, meta):
    text = "Die Bürger zahlen 5 € für größere Straßen."
    html = ARTICLE_HTML.replace("<head>", f"<head>{meta}").replace(
        "Die Stadt plant neue Radwege entlang des Flusses.", text
    )
    source = _source(
        lambda request: httpx.Response(200, content=html.encode("iso-8859-15"), headers={"Content-Type": content_type})
    )

    article = asyncio.run(source.fetch("https://www.tagesspiegel.de/a"))

    assert text in article.content


def test_fetch_uses_domain_when_page_has_no_site_name():
    html = ARTICLE_HTML.replace('<meta property="og:site_name" content="Tagesspiegel">', "")
    source = _source(lambda request: httpx.Response(200, html=html))

    article = asyncio.run(source.fetch("https://www.tagesspiegel.de/a"))

    assert article.source_name == "tagesspiegel.de"  # trafilatura fills sitename from the URL


def test_fetch_page_without_text_raises_value_error():
    source = _source(lambda request: httpx.Response(200, html="<html><body></body></html>"))
    with pytest.raises(ValueError, match="Could not extract"):
        asyncio.run(source.fetch("https://example.org/empty"))


def test_fetch_http_status_error_becomes_value_error():
    source = _source(lambda request: httpx.Response(403))
    with pytest.raises(ValueError, match=r"HTTP 403\). Pick another article"):
        asyncio.run(source.fetch("https://www.zeit.de/a"))


def test_fetch_timeout_becomes_value_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ValueError, match=r"ReadTimeout\). Pick another article"):
        asyncio.run(_source(handler).fetch("https://example.org/slow"))

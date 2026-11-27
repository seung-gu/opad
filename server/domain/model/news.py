"""News article found by a news source."""

from pydantic import BaseModel, ConfigDict


class NewsArticle(BaseModel):
    """A news article from a news source. `content` is set only when one article is fetched."""

    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    source_name: str
    date: str | None = None
    author: str | None = None
    content: str | None = None

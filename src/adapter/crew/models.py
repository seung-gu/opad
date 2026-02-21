"""Pydantic models for CrewAI task outputs."""

from pydantic import BaseModel, Field
from typing import Optional

from domain.model.article import EditRecord, SourceInfo


class NewsArticle(BaseModel):
    """A news article with source information."""
    title: str = Field(description="Article title")
    source_name: str = Field(description="Publication or news outlet name")
    source_url: Optional[str] = Field(description="Source URL if available", default=None)
    publication_date: Optional[str] = Field(description="Publication date", default=None)
    author: Optional[str] = Field(description="Author name if available", default=None)
    content: str = Field(description="Full article content/text")

    def to_source_info(self) -> SourceInfo:
        """Convert to domain SourceInfo value object."""
        return SourceInfo(
            title=self.title,
            source_name=self.source_name,
            source_url=self.source_url,
            author=self.author,
            publication_date=self.publication_date,
        )


class NewsArticleList(BaseModel):
    """A list of news articles."""
    articles: list[NewsArticle] = Field(description="List of 2-3 news articles")


class SelectedArticle(BaseModel):
    """A selected news article with selection rationale."""
    article: NewsArticle = Field(description="The selected news article")
    selection_rationale: str = Field(description="Explanation of why this article was selected over the alternatives")


class ReplacedSentence(BaseModel):
    """Replaced sentence information (kept for CrewAI LLM output compatibility)."""
    original: str = Field(description="The original sentence before replacement")
    replaced: str = Field(description="The sentence after replacement")
    rationale: str = Field(description="Reason for the replacement")

    def to_edit_record(self) -> EditRecord:
        """Convert to domain EditRecord value object."""
        return EditRecord(
            original=self.original,
            replaced=self.replaced,
            rationale=self.rationale,
        )


class ReviewedArticle(BaseModel):
    """A reviewed news article with review rationale."""
    article_content: str = Field(description="The final polished article in markdown format")
    replaced_sentences: list[ReplacedSentence] = Field(
        description="List of sentences that were replaced during review",
        default=[],
    )

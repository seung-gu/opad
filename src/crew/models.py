"""Pydantic models for CrewAI task outputs."""

from pydantic import BaseModel, Field
from typing import Optional


class NewsArticle(BaseModel):
    """A news article with source information"""
    title: str = Field(description="Article title")
    source_name: str = Field(description="Publication or news outlet name")
    source_url: Optional[str] = Field(description="Source URL if available", default=None)
    publication_date: Optional[str] = Field(description="Publication date", default=None)
    author: Optional[str] = Field(description="Author name if available", default=None)
    content: str = Field(description="Full article content/text")


class NewsArticleList(BaseModel):
    """A list of news articles"""
    articles: list[NewsArticle] = Field(description="List of 2-3 news articles")


class SelectedArticle(BaseModel):
    """A selected news article with selection rationale"""
    article: NewsArticle = Field(description="The selected news article")
    selection_rationale: str = Field(description="Explanation of why this article was selected over the alternatives")

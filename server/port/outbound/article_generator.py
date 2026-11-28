"""Port definition for ArticleGenerator."""

from typing import Protocol

from domain.model.article import ArticleInputs, GenerationResult


class ArticleGeneratorPort(Protocol):
    def generate(
        self,
        inputs: ArticleInputs,
        vocabulary: list[str],
        job_id: str = "",
        article_id: str = "",
    ) -> GenerationResult: ...

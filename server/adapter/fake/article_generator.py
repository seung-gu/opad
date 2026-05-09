"""In-memory implementation of ArticleGeneratorPort for testing."""

from domain.model.article import (
    ArticleInputs, GenerationResult, SourceInfo,
)


class FakeArticleGenerator:
    def __init__(self, content: str = "# Test Article\n\nGenerated content."):
        self.content = content
        self.generate_called = False

    def generate(
        self,
        inputs: ArticleInputs,
        vocabulary: list[str],
        job_id: str = "",
        article_id: str = "",
    ) -> GenerationResult:
        self.generate_called = True
        return GenerationResult(
            content=self.content,
            source=SourceInfo(title="Test", source_name="Test Source"),
            edit_history=[],
            agent_usage=[],
        )

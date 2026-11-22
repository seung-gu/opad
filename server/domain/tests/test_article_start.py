"""Tests for the start stage on Article and ArticleInputs."""

from domain.model.article import Article, ArticleInputs, ArticleStatus, SourceInfo

TEXT = "Ein Text."
SOURCE = SourceInfo(title="Titel", source_name="Zeitung")


def test_inputs_start_defaults_to_find():
    inputs = ArticleInputs(language="German", level="B1", length="300", topic="AI")
    assert inputs.start == "find"


def test_create_find_keeps_today_behaviour():
    article = Article.create(ArticleInputs(language="German", level="B1", length="300", topic="AI"), "u1")
    assert article.inputs.start == "find"
    assert article.content is None
    assert article.source is None
    assert article.status is ArticleStatus.RUNNING


def test_set_content_puts_in_the_given_text_and_source():
    article = Article.create(ArticleInputs(language="German", level="B1", start="rewrite"), "u1")

    article.set_content(TEXT, SOURCE)

    assert (article.content, article.source) == (TEXT, SOURCE)
    assert article.status is ArticleStatus.RUNNING

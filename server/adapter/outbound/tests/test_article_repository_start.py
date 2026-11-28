"""Tests for start in the Mongo article repository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from adapter.outbound.mongodb.article_repository import MongoArticleRepository
from domain.model.article import Article, ArticleInputs

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _mongo_repo() -> tuple[MongoArticleRepository, MagicMock]:
    collection = MagicMock()
    db = MagicMock()
    db.__getitem__.return_value = collection
    return MongoArticleRepository(db), collection


def _doc(**overrides) -> dict:
    doc = {
        "_id": "a1",
        "inputs": {"language": "German", "level": "B1", "length": "300", "topic": "AI"},
        "status": "running",
        "created_at": NOW,
        "updated_at": NOW,
    }
    doc.update(overrides)
    return doc


def test_mongo_save_stores_start_and_the_given_text():
    repo, collection = _mongo_repo()
    article = Article.create(ArticleInputs(language="German", level="B1", start="rewrite"), "u1")
    article.set_content("Ein Text.")

    assert repo.save(article)

    saved = collection.update_one.call_args.args[1]["$set"]
    assert saved["inputs"]["start"] == "rewrite"
    assert saved["content"] == "Ein Text."


def test_mongo_reads_document_saved_before_start_existed_as_find():
    repo, collection = _mongo_repo()
    collection.find_one.return_value = _doc()

    article = repo.get_by_id("a1")

    assert article.inputs.start == "find"


def test_mongo_reads_start_back():
    repo, collection = _mongo_repo()
    collection.find_one.return_value = _doc(
        inputs={"language": "German", "level": "B1", "length": None, "topic": None, "start": "rewrite"},
        content="Ein Text.",
    )

    article = repo.get_by_id("a1")

    assert article.inputs.start == "rewrite"
    assert article.content == "Ein Text."

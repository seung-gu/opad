from fastapi import HTTPException

from adapter.mongodb.connection import get_mongodb_client, DATABASE_NAME
from adapter.mongodb.article_repository import MongoArticleRepository
from port.article_repository import ArticleRepository


def get_article_repo() -> ArticleRepository:
    client = get_mongodb_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    db = client[DATABASE_NAME]
    return MongoArticleRepository(db)
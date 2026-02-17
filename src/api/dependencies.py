from fastapi import HTTPException

from adapter.external.free_dictionary import FreeDictionaryAdapter
from adapter.external.litellm import LiteLLMAdapter
from adapter.mongodb.connection import get_mongodb_client, DATABASE_NAME
from adapter.mongodb.article_repository import MongoArticleRepository
from adapter.mongodb.token_usage_repository import MongoTokenUsageRepository
from adapter.mongodb.user_repository import MongoUserRepository
from adapter.mongodb.vocabulary_repository import MongoVocabularyRepository
from port.article_repository import ArticleRepository
from port.dictionary import DictionaryPort
from port.llm import LLMPort
from port.token_usage_repository import TokenUsageRepository
from port.user_repository import UserRepository
from port.vocabulary_repository import VocabularyRepository


def _get_db():
    """Get MongoDB database, raising 503 if unavailable."""
    client = get_mongodb_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return client[DATABASE_NAME]


def get_article_repo() -> ArticleRepository:
    return MongoArticleRepository(_get_db())


def get_user_repo() -> UserRepository:
    return MongoUserRepository(_get_db())


def get_token_usage_repo() -> TokenUsageRepository:
    return MongoTokenUsageRepository(_get_db())


def get_vocab_repo() -> VocabularyRepository:
    return MongoVocabularyRepository(_get_db())


def get_dictionary_port() -> DictionaryPort:
    return FreeDictionaryAdapter()


def get_llm_port() -> LLMPort:
    return LiteLLMAdapter()

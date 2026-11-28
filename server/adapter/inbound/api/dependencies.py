from functools import lru_cache

from fastapi import HTTPException

from adapter.outbound.free_dictionary import FreeDictionaryAdapter
from adapter.outbound.litellm import LiteLLMAdapter
from adapter.outbound.mongodb.article_repository import MongoArticleRepository
from adapter.outbound.mongodb.connection import DATABASE_NAME, get_mongodb_client
from adapter.outbound.mongodb.token_usage_repository import MongoTokenUsageRepository
from adapter.outbound.mongodb.user_repository import MongoUserRepository
from adapter.outbound.mongodb.vocabulary_repository import MongoVocabularyRepository
from adapter.outbound.redis_job_queue import RedisJobQueueAdapter
from adapter.outbound.stanza import StanzaAdapter
from port.outbound.dictionary import DictionaryPort
from port.outbound.job_queue import JobQueuePort
from port.outbound.llm import LLMPort
from port.outbound.nlp import NLPPort
from port.outbound.repository.article import ArticleRepository
from port.outbound.repository.token_usage import TokenUsageRepository
from port.outbound.repository.user import UserRepository
from port.outbound.repository.vocabulary import VocabularyRepository


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


def get_job_queue() -> JobQueuePort:
    return RedisJobQueueAdapter()


@lru_cache(maxsize=1)
def get_nlp_port() -> NLPPort:
    """Get NLP port (Stanza adapter singleton for German lemma extraction)."""
    return StanzaAdapter()

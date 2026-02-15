"""MongoDB index management utilities.

Shared index creation with conflict resolution, used by each MongoXxxRepository.
"""

from logging import getLogger

from pymongo.errors import PyMongoError

logger = getLogger(__name__)


def create_index_safe(collection, keys: list, name: str, **kwargs) -> bool:
    """Create index with conflict resolution.

    Handles two conflict scenarios:
    - Same name but different key spec (schema migration)
    - Same key spec but different name (rename)

    In both cases, drops the conflicting index and recreates with the desired spec.
    """
    try:
        collection.create_index(keys, name=name, **kwargs)
        return True
    except PyMongoError as e:
        if "already exists" not in str(e) and "Conflict" not in str(e):
            raise
        return _resolve_conflict(collection, keys, name, **kwargs)


def _resolve_conflict(collection, keys: list, name: str, **kwargs) -> bool:
    """Drop conflicting index and recreate."""
    keys_dict = dict(keys)

    for idx_name, idx_info in collection.index_information().items():
        if idx_name == '_id_':
            continue

        idx_keys = dict(idx_info.get('key', []))
        same_name = idx_name == name
        same_keys = idx_keys == keys_dict

        if (same_name and not same_keys) or (same_keys and not same_name):
            logger.warning(f"Dropping conflicting index: {idx_name}")
            collection.drop_index(idx_name)
            collection.create_index(keys, name=name, **kwargs)
            logger.info(f"Recreated index: {name}")
            return True

    logger.error(f"Failed to resolve index conflict for {name}")
    return False


def ensure_all_indexes(db) -> bool:
    """Ensure indexes for all collections. Called at app startup."""
    from adapter.mongodb.article_repository import MongoArticleRepository
    from adapter.mongodb.user_repository import MongoUserRepository
    from adapter.mongodb.vocabulary_repository import MongoVocabularyRepository
    from adapter.mongodb.token_usage_repository import MongoTokenUsageRepository

    results = [
        MongoArticleRepository(db).ensure_indexes(),
        MongoUserRepository(db).ensure_indexes(),
        MongoVocabularyRepository(db).ensure_indexes(),
        MongoTokenUsageRepository(db).ensure_indexes(),
    ]
    return all(results)

"""MongoDB operational statistics — not entity-specific, used by /stats endpoint."""

from logging import getLogger
from typing import Optional

from pymongo.errors import PyMongoError

from adapter.mongodb import COLLECTION_NAME, VOCABULARY_COLLECTION_NAME

logger = getLogger(__name__)


def get_database_stats(db) -> Optional[dict]:
    """Get articles collection statistics."""
    try:
        collection = db[COLLECTION_NAME]

        coll_stats = db.command("collStats", COLLECTION_NAME)

        total_count = collection.count_documents({})
        deleted_count = collection.count_documents({'status': 'deleted'})
        running_count = collection.count_documents({'status': 'running'})
        failed_count = collection.count_documents({'status': 'failed'})
        completed_count = collection.count_documents({'status': 'completed'})
        active_count = total_count - deleted_count

        data_size_bytes = coll_stats.get('size', 0)
        index_size_bytes = coll_stats.get('totalIndexSize', 0)
        storage_size_bytes = coll_stats.get('storageSize', 0)
        total_size_bytes = coll_stats.get('totalSize', storage_size_bytes + index_size_bytes)

        data_size_mb = data_size_bytes / (1024 * 1024)
        index_size_mb = index_size_bytes / (1024 * 1024)
        storage_size_mb = storage_size_bytes / (1024 * 1024)
        total_size_mb = total_size_bytes / (1024 * 1024)

        return {
            'total_documents': total_count,
            'active_documents': active_count,
            'deleted_documents': deleted_count,
            'running_documents': running_count,
            'failed_documents': failed_count,
            'completed_documents': completed_count,
            'data_size_mb': round(data_size_mb, 2),
            'data_size_bytes': data_size_bytes,
            'index_size_mb': round(index_size_mb, 2),
            'index_size_bytes': index_size_bytes,
            'storage_size_mb': round(storage_size_mb, 2),
            'storage_size_bytes': storage_size_bytes,
            'total_size_mb': round(total_size_mb, 2),
            'total_size_bytes': total_size_bytes,
            'avg_document_size_bytes': round(coll_stats.get('avgObjSize', 0), 2),
        }
    except PyMongoError as e:
        logger.error("Failed to get database stats", extra={"error": str(e)})
        return None


def get_vocabulary_stats(db) -> Optional[dict]:
    """Get vocabularies collection statistics."""
    try:
        collection = db[VOCABULARY_COLLECTION_NAME]

        coll_stats = db.command("collStats", VOCABULARY_COLLECTION_NAME)

        total_count = collection.count_documents({})

        language_counts = {}
        for doc in collection.aggregate([
            {'$group': {'_id': '$language', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]):
            lang = doc.get('_id') or 'Unknown'
            language_counts[lang] = doc.get('count', 0)

        data_size_bytes = coll_stats.get('size', 0)
        index_size_bytes = coll_stats.get('totalIndexSize', 0)
        storage_size_bytes = coll_stats.get('storageSize', 0)
        total_size_bytes = coll_stats.get('totalSize', storage_size_bytes + index_size_bytes)

        data_size_mb = data_size_bytes / (1024 * 1024)
        index_size_mb = index_size_bytes / (1024 * 1024)
        storage_size_mb = storage_size_bytes / (1024 * 1024)
        total_size_mb = total_size_bytes / (1024 * 1024)

        return {
            'total_documents': total_count,
            'data_size_mb': round(data_size_mb, 2),
            'data_size_bytes': data_size_bytes,
            'index_size_mb': round(index_size_mb, 2),
            'index_size_bytes': index_size_bytes,
            'storage_size_mb': round(storage_size_mb, 2),
            'storage_size_bytes': storage_size_bytes,
            'total_size_mb': round(total_size_mb, 2),
            'total_size_bytes': total_size_bytes,
            'avg_document_size_bytes': round(coll_stats.get('avgObjSize', 0), 2),
            'by_language': language_counts,
        }
    except PyMongoError as e:
        logger.error("Failed to get vocabulary stats", extra={"error": str(e)})
        return None

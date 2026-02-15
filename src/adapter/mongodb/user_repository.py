"""MongoDB implementation of UserRepository."""

import uuid
from datetime import datetime, timezone
from logging import getLogger
from pymongo.database import Database
from pymongo.errors import PyMongoError
from adapter.mongodb import USERS_COLLECTION_NAME
from domain.model.user import User

logger = getLogger(__name__)


class MongoUserRepository:
    def __init__(self, db: Database):
        self.collection = db[USERS_COLLECTION_NAME]
    
    def ensure_indexes(self) -> bool:
        """Create indexes for users collection."""
        from adapter.mongodb.indexes import create_index_safe

        try:
            create_index_safe(self.collection, [('email', 1)], 'idx_users_email', unique=True)
            create_index_safe(self.collection, [('created_at', -1)], 'idx_users_created_at')
            return True
        except Exception as e:
            logger.error("Failed to create users indexes", extra={"error": str(e)})
            return False

    def _to_domain(self, doc: dict) -> User:
        """Convert MongoDB document to User domain model."""
        return User(
            id=doc['_id'],
            name=doc['name'],
            email=doc['email'],
            created_at=doc['created_at'],
            updated_at=doc['updated_at'],
            last_login=doc.get('last_login'),
            password_hash=doc.get('password_hash'),
            provider=doc.get('provider', 'email'),
        )

    def create(self, email: str, password_hash: str, name: str) -> User | None:
        """Create a new user and return the User object."""
        try:
            # Create user document
            user_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            user_doc = {
                '_id': user_id,
                'email': email,
                'password_hash': password_hash,
                'name': name,
                'created_at': now,
                'updated_at': now,
                'provider': 'email'
            }
            self.collection.insert_one(user_doc)
            
            user = self._to_domain(user_doc)
            logger.info("User created", extra={"userId": user_id, "email": email})
            return user
        except PyMongoError as e:
            error_str = str(e)
            if 'duplicate key' in error_str.lower() or 'E11000' in error_str:
                logger.warning("User creation failed: email already exists", extra={"email": email})
            else:
                logger.error("Failed to create user", extra={"email": email, "error": error_str})
            return None

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email. Return User or None if not found."""
        try:
            user = self.collection.find_one({'email': email})
            if user:
                user = self._to_domain(user)
                return user
            return None
        except PyMongoError as e:
            logger.error("Failed to get user by email", extra={"email": email, "error": str(e)})
            return None

    def get_by_id(self, user_id: str) -> User | None:
        """Find a user by ID. Return User or None if not found."""
        try:
            user = self.collection.find_one({'_id': user_id})
            if user:
                user = self._to_domain(user)
                return user
            return None
        except PyMongoError as e:
            logger.error("Failed to get user by ID", extra={"userId": user_id, "error": str(e)})
            return None
    
    def update_last_login(self, user_id: str) -> bool:
        """Update the last login timestamp for a user. Return True if successful."""
        try:
            now = datetime.now(timezone.utc)
            result = self.collection.update_one(
                {'_id': user_id},
                {'$set': {'last_login': now, 'updated_at': now}}
            )
            if result.modified_count > 0:
                logger.debug("Updated last_login", extra={"userId": user_id})
                return True
            return False
        except PyMongoError as e:
            logger.error("Failed to update last_login", extra={"userId": user_id, "error": str(e)})
            return False
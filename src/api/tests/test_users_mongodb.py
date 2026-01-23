"""Tests for Users MongoDB functions."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError, PyMongoError

# Add src to path
# test_users_mongodb.py is at /app/src/api/tests/test_users_mongodb.py
# src is at /app/src, so we go up 3 levels
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.mongodb import (
    get_user,
    create_user,
    get_user_by_id,
    _ensure_users_indexes,
    USERS_COLLECTION_NAME
)


class TestGetUser(unittest.TestCase):
    """Test get_user() function."""
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_success(self, mock_get_client):
        """Test successful user retrieval by email."""
        # Mock MongoDB client and collection
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock user document
        mock_user = {
            '_id': 'test-user-id',
            'email': 'test@example.com',
            'name': 'Test User',
            'password_hash': 'hashed_password',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'provider': 'email'
        }
        mock_collection.find_one.return_value = mock_user
        
        # Call function
        result = get_user('test@example.com')
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test-user-id')
        self.assertEqual(result['email'], 'test@example.com')
        self.assertEqual(result['name'], 'Test User')
        self.assertNotIn('_id', result)  # _id should be converted to id
        mock_collection.find_one.assert_called_once_with({'email': 'test@example.com'})
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_not_found(self, mock_get_client):
        """Test get_user() when user doesn't exist."""
        # Mock MongoDB client
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock no user found
        mock_collection.find_one.return_value = None
        
        # Call function
        result = get_user('nonexistent@example.com')
        
        # Verify
        self.assertIsNone(result)
        mock_collection.find_one.assert_called_once_with({'email': 'nonexistent@example.com'})
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_no_connection(self, mock_get_client):
        """Test get_user() when MongoDB is unavailable."""
        mock_get_client.return_value = None
        
        result = get_user('test@example.com')
        
        self.assertIsNone(result)


class TestCreateUser(unittest.TestCase):
    """Test create_user() function."""
    
    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.uuid')
    @patch('utils.mongodb.datetime')
    def test_create_user_success(self, mock_datetime, mock_uuid, mock_get_client):
        """Test successful user creation."""
        # Mock UUID generation
        mock_uuid.uuid4.return_value.hex = 'new-user-id-123'
        
        # Mock datetime
        mock_now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Mock MongoDB client and collection
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Call function
        result = create_user(
            email='newuser@example.com',
            password_hash='$2b$12$hashedpassword',
            name='New User'
        )
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'new-user-id-123')
        self.assertEqual(result['email'], 'newuser@example.com')
        self.assertEqual(result['name'], 'New User')
        self.assertEqual(result['password_hash'], '$2b$12$hashedpassword')
        self.assertEqual(result['created_at'], mock_now)
        self.assertEqual(result['updated_at'], mock_now)
        self.assertEqual(result['provider'], 'email')
        
        # Verify insert_one was called with correct document
        mock_collection.insert_one.assert_called_once()
        # Note: insert_one() receives user_doc dict, then user_doc.pop('_id') modifies it
        # So call_args will show 'id' instead of '_id' after the modification
        # We verify the call happened and check the result instead
        call_args = mock_collection.insert_one.call_args[0][0]
        # The dict was modified after insert_one, so _id became id
        # We verify the important fields are present
        self.assertEqual(call_args.get('id') or call_args.get('_id'), 'new-user-id-123')
        self.assertEqual(call_args['email'], 'newuser@example.com')
        self.assertEqual(call_args['name'], 'New User')
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_create_user_duplicate_email(self, mock_get_client):
        """Test create_user() fails when email already exists."""
        # Mock MongoDB client
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock duplicate key error
        mock_collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key")
        
        # Call function
        result = create_user(
            email='existing@example.com',
            password_hash='$2b$12$hashedpassword',
            name='Existing User'
        )
        
        # Verify
        self.assertIsNone(result)
        mock_collection.insert_one.assert_called_once()
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_create_user_no_connection(self, mock_get_client):
        """Test create_user() when MongoDB is unavailable."""
        mock_get_client.return_value = None
        
        result = create_user(
            email='test@example.com',
            password_hash='$2b$12$hashedpassword',
            name='Test User'
        )
        
        self.assertIsNone(result)


class TestGetUserById(unittest.TestCase):
    """Test get_user_by_id() function."""
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_by_id_success(self, mock_get_client):
        """Test successful user retrieval by ID."""
        # Mock MongoDB client and collection
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock user document
        mock_user = {
            '_id': 'test-user-id',
            'email': 'test@example.com',
            'name': 'Test User',
            'password_hash': 'hashed_password',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'provider': 'email'
        }
        mock_collection.find_one.return_value = mock_user
        
        # Call function
        result = get_user_by_id('test-user-id')
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test-user-id')
        self.assertEqual(result['email'], 'test@example.com')
        self.assertNotIn('_id', result)  # _id should be converted to id
        mock_collection.find_one.assert_called_once_with({'_id': 'test-user-id'})
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_by_id_not_found(self, mock_get_client):
        """Test get_user_by_id() when user doesn't exist."""
        # Mock MongoDB client
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock no user found
        mock_collection.find_one.return_value = None
        
        # Call function
        result = get_user_by_id('nonexistent-id')
        
        # Verify
        self.assertIsNone(result)
        mock_collection.find_one.assert_called_once_with({'_id': 'nonexistent-id'})
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_by_id_no_connection(self, mock_get_client):
        """Test get_user_by_id() when MongoDB is unavailable."""
        mock_get_client.return_value = None
        
        result = get_user_by_id('test-user-id')
        
        self.assertIsNone(result)


class TestEnsureUsersIndexes(unittest.TestCase):
    """Test _ensure_users_indexes() function."""
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_users_indexes_success(self, mock_get_client):
        """Test successful index creation."""
        # Mock MongoDB client and collection
        mock_collection = MagicMock()
        mock_collection.list_indexes.return_value = [
            {'name': '_id_', 'key': {'_id': 1}}
        ]
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Call function
        result = _ensure_users_indexes()
        
        # Verify
        self.assertTrue(result)
        # Verify create_index was called for both indexes
        self.assertEqual(mock_collection.create_index.call_count, 2)
        
        # Verify email unique index
        email_call = mock_collection.create_index.call_args_list[0]
        self.assertEqual(email_call[0][0], [('email', 1)])
        self.assertEqual(email_call[1]['name'], 'idx_users_email')
        self.assertTrue(email_call[1]['unique'])
        
        # Verify created_at index
        created_at_call = mock_collection.create_index.call_args_list[1]
        self.assertEqual(created_at_call[0][0], [('created_at', -1)])
        self.assertEqual(created_at_call[1]['name'], 'idx_users_created_at')
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_users_indexes_no_connection(self, mock_get_client):
        """Test _ensure_users_indexes() when MongoDB is unavailable."""
        mock_get_client.return_value = None
        
        result = _ensure_users_indexes()
        
        self.assertFalse(result)
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_users_indexes_handles_existing_indexes(self, mock_get_client):
        """Test _ensure_users_indexes() handles existing indexes gracefully."""
        # Mock MongoDB client and collection
        mock_collection = MagicMock()
        mock_collection.list_indexes.return_value = [
            {'name': '_id_', 'key': {'_id': 1}},
            {'name': 'idx_users_email', 'key': {'email': 1}},
            {'name': 'idx_users_created_at', 'key': {'created_at': -1}}
        ]
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Call function (should be idempotent)
        result = _ensure_users_indexes()
        
        # Verify
        self.assertTrue(result)
        # Indexes should still be created/verified (idempotent operation)
        self.assertEqual(mock_collection.create_index.call_count, 2)


class TestUserEmailUniqueness(unittest.TestCase):
    """Test that email uniqueness is enforced."""
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_duplicate_email_prevention(self, mock_get_client):
        """Test that creating a user with duplicate email fails."""
        # Mock MongoDB client
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # First user creation succeeds
        mock_collection.insert_one.return_value = None
        
        # Create first user
        result1 = create_user(
            email='duplicate@example.com',
            password_hash='$2b$12$hash1',
            name='First User'
        )
        self.assertIsNotNone(result1)
        
        # Second user creation with same email fails
        mock_collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error")
        
        result2 = create_user(
            email='duplicate@example.com',
            password_hash='$2b$12$hash2',
            name='Second User'
        )
        
        # Verify second creation failed
        self.assertIsNone(result2)
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_unique_index_creation(self, mock_get_client):
        """Test that unique index on email is created."""
        # Mock MongoDB client
        mock_collection = MagicMock()
        mock_collection.list_indexes.return_value = [{'name': '_id_', 'key': {'_id': 1}}]
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Call function
        _ensure_users_indexes()
        
        # Verify unique index was created
        email_index_call = None
        for call in mock_collection.create_index.call_args_list:
            if call[1].get('name') == 'idx_users_email':
                email_index_call = call
                break
        
        self.assertIsNotNone(email_index_call)
        self.assertTrue(email_index_call[1]['unique'])


class TestIndexConflictHandling(unittest.TestCase):
    """Test _ensure_users_indexes() index conflict handling."""
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_index_handles_conflict(self, mock_get_client):
        """Test that conflicting indexes are dropped and recreated."""
        from pymongo.errors import PyMongoError
        
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock: First create_index call raises conflict error
        call_count = {'count': 0}
        def create_index_side_effect(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                # First call: simulate index conflict
                raise PyMongoError("Index already exists with a different name")
            # Subsequent calls succeed
            return 'idx_users_email'
        
        mock_collection.create_index.side_effect = create_index_side_effect
        
        # Mock existing conflicting index
        mock_collection.list_indexes.return_value = [
            {'name': '_id_', 'key': {'_id': 1}},
            {'name': 'old_email_idx', 'key': {'email': 1}}  # Conflicting index
        ]
        
        result = _ensure_users_indexes()
        
        # Verify conflict was resolved
        self.assertTrue(result)
        # Should have tried to create, then dropped conflicting, then recreated
        self.assertGreaterEqual(mock_collection.create_index.call_count, 2)
        # Verify drop_index was called for conflicting index
        mock_collection.drop_index.assert_called_with('old_email_idx')
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_index_drop_failure(self, mock_get_client):
        """Test _ensure_index() when drop_index fails."""
        from pymongo.errors import PyMongoError
        
        mock_collection = MagicMock()
        mock_collection.list_indexes.return_value = [
            {'name': '_id_', 'key': {'_id': 1}},
            {'name': 'conflicting_idx', 'key': {'email': 1}}
        ]
        # First create_index raises conflict
        # drop_index fails
        call_count = {'count': 0}
        def create_index_side_effect(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise PyMongoError("Index already exists with a different name")
            return 'idx_users_email'
        
        mock_collection.create_index.side_effect = create_index_side_effect
        mock_collection.drop_index.side_effect = PyMongoError("Drop failed")
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        result = _ensure_users_indexes()
        self.assertFalse(result)  # Should fail when drop fails
    
    @patch('utils.mongodb.get_mongodb_client')
    def test_ensure_index_other_pymongo_error(self, mock_get_client):
        """Test _ensure_index() with non-conflict PyMongoError."""
        from pymongo.errors import PyMongoError
        
        mock_collection = MagicMock()
        mock_collection.list_indexes.return_value = [{'name': '_id_', 'key': {'_id': 1}}]
        mock_collection.create_index.side_effect = PyMongoError("Other database error")
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        result = _ensure_users_indexes()
        self.assertFalse(result)  # Should fail on other errors


if __name__ == '__main__':
    unittest.main()

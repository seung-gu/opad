"""Comprehensive tests for Redis queue operations."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import json
from datetime import datetime

# Add src to path
# test_queue.py is at /app/src/api/tests/test_queue.py
# src is at /app/src, so we go up 3 levels
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.job_queue import enqueue_job, get_job_status, update_job_status, get_redis_client
from worker.processor import process_job
from adapter.fake.article_repository import FakeArticleRepository
from domain.model.article import ArticleInputs
import api.job_queue as queue_module


class TestQueueBasics(unittest.TestCase):
    """Basic queue operation tests."""
    
    @patch('api.job_queue.get_redis_client')
    def test_job_lifecycle(self, mock_get_redis):
        """Test complete job lifecycle: enqueue -> process -> status update."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        # No existing data initially
        mock_redis.get.return_value = None
        
        # Test enqueue
        job_id = "test-job-123"
        article_id = "test-article-456"
        inputs = {'language': 'German', 'level': 'B2', 'length': '500', 'topic': 'AI'}
        
        result = enqueue_job(job_id, article_id, inputs)
        self.assertTrue(result)
        mock_redis.rpush.assert_called_once()
        
        # Test status update
        update_job_status(
            job_id=job_id,
            status='running',
            progress=50,
            message='Processing...'
        )
        mock_redis.setex.assert_called()
        
        # Test status retrieval
        mock_redis.get.return_value = '{"id": "test-job-123", "status": "running", "progress": 50}'
        status = get_job_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], 'running')
    
    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_end_to_end_job_processing(self, mock_listener,
                                        mock_run_crew, mock_update_status):
        """Test end-to-end job processing flow."""
        repo = FakeArticleRepository()
        repo.save_metadata(
            article_id='e2e-test-article',
            inputs=ArticleInputs(language='German', level='B2', length='500', topic='AI'),
            user_id='test-user-789',
        )

        job_data = {
            'job_id': 'e2e-test-job',
            'article_id': 'e2e-test-article',
            'user_id': 'test-user-789',
            'inputs': {'language': 'German', 'level': 'B2', 'length': '500', 'topic': 'AI'}
        }

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.raw = "# Test Article\n\nContent"
        mock_result.pydantic.article_content = "# Test Article\n\nContent"
        mock_result.pydantic.replaced_sentences = []
        mock_run_crew.return_value = mock_result

        mock_listener_instance = MagicMock()
        mock_listener_instance.task_failed = False
        mock_listener.return_value = mock_listener_instance

        # Execute
        result = process_job(job_data, repo)

        # Verify
        self.assertTrue(result)
        # Should update status multiple times: running -> completed
        self.assertGreaterEqual(mock_update_status.call_count, 2)

        # Check final status update (positional args: job_id, status, progress, message)
        final_call = mock_update_status.call_args_list[-1]
        args, _ = final_call
        self.assertEqual(args[1], 'completed')  # status
        self.assertEqual(args[2], 100)  # progress


class TestRedisReconnection(unittest.TestCase):
    """Test Redis client reconnection after connection loss."""
    
    def setUp(self):
        """Reset global state before each test."""
        queue_module._redis_client_cache = None
        queue_module._redis_connection_attempted = False
        queue_module._redis_connection_failed = False
    
    @patch('api.job_queue.REDIS_URL', 'redis://localhost:6379')
    @patch('redis.from_url')
    def test_reconnection_after_cached_client_failure(self, mock_from_url):
        """Test that reconnection is attempted after cached client fails ping."""
        # Mock successful initial connection
        mock_client1 = MagicMock()
        mock_client1.ping.return_value = True
        mock_from_url.return_value = mock_client1
        
        # First call - should connect and cache
        client1 = get_redis_client()
        self.assertIsNotNone(client1)
        self.assertEqual(queue_module._redis_client_cache, mock_client1)
        self.assertTrue(queue_module._redis_connection_attempted)
        
        # Simulate cached client failure (ping fails)
        mock_client1.ping.side_effect = Exception("Connection lost")
        
        # Mock new connection for reconnection
        mock_client2 = MagicMock()
        mock_client2.ping.return_value = True
        mock_from_url.return_value = mock_client2
        
        # Second call - should detect cache failure and reconnect
        client2 = get_redis_client()
        self.assertIsNotNone(client2)
        self.assertEqual(queue_module._redis_client_cache, mock_client2)
        # Should have attempted reconnection (not blocked by _redis_connection_attempted)
        self.assertEqual(mock_from_url.call_count, 2)
    
    @patch('api.job_queue.REDIS_URL', 'redis://localhost:6379')
    @patch('redis.from_url')
    def test_no_reconnection_after_initial_failure(self, mock_from_url):
        """Test that initial connection failure prevents retries."""
        from redis.exceptions import RedisError
        
        # Mock initial connection failure (ping fails with RedisError)
        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisError("Connection refused")
        mock_from_url.return_value = mock_client
        
        # First call - should fail and mark as failed
        client1 = get_redis_client()
        self.assertIsNone(client1)
        self.assertTrue(queue_module._redis_connection_failed)
        
        # Second call - should return None immediately without retry
        client2 = get_redis_client()
        self.assertIsNone(client2)
        # Should not have attempted another connection (only one attempt)
        self.assertEqual(mock_from_url.call_count, 1)
    
    @patch('api.job_queue.REDIS_URL', 'redis://localhost:6379')
    @patch('redis.from_url')
    def test_first_connection_logs_successfully(self, mock_from_url):
        """Test that first connection logs 'Connected successfully'."""
        # Mock successful connection
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client
        
        with self.assertLogs('api.job_queue', level='INFO') as log_context:
            client = get_redis_client()
            self.assertIsNotNone(client)
            
            # Should log "Connected successfully" on first connection
            self.assertTrue(
                any('[REDIS] Connected successfully' in msg for msg in log_context.output),
                "First connection should log 'Connected successfully'"
            )
    
    @patch('api.job_queue.REDIS_URL', 'redis://localhost:6379')
    @patch('redis.from_url')
    def test_reconnection_does_not_log_as_first_connection(self, mock_from_url):
        """Test that reconnection does NOT log 'Connected successfully'."""
        # Step 1: First successful connection
        mock_client1 = MagicMock()
        mock_client1.ping.return_value = True
        mock_from_url.return_value = mock_client1
        
        with self.assertLogs('api.job_queue', level='DEBUG') as log_context1:
            client1 = get_redis_client()
            self.assertIsNotNone(client1)
            
            # First connection should log
            self.assertTrue(
                any('[REDIS] Connected successfully' in msg for msg in log_context1.output),
                "First connection should log"
            )
        
        # Step 2: Simulate connection loss (ping fails)
        mock_client1.ping.side_effect = Exception("Connection lost")
        
        # Step 3: Reconnect
        mock_client2 = MagicMock()
        mock_client2.ping.return_value = True
        mock_from_url.return_value = mock_client2
        
        with self.assertLogs('api.job_queue', level='DEBUG') as log_context2:
            client2 = get_redis_client()
            self.assertIsNotNone(client2)
            
            # Reconnection should NOT log "Connected successfully"
            self.assertFalse(
                any('[REDIS] Connected successfully' in msg for msg in log_context2.output),
                "Reconnection should NOT log 'Connected successfully'"
            )
            
            # Should log reconnection attempt
            self.assertTrue(
                any('attempting reconnection' in msg for msg in log_context2.output),
                "Should log reconnection attempt"
            )


class TestJobStatusFields(unittest.TestCase):
    """Test job status field storage and preservation."""
    
    @patch('api.job_queue.get_redis_client')
    def test_article_id_storage(self, mock_get_redis):
        """Test that article_id is stored in status data."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.get.return_value = None
        
        job_id = "test-job-123"
        article_id = "test-article-456"
        
        result = update_job_status(
            job_id=job_id,
            status='queued',
            progress=0,
            message='Test',
            article_id=article_id
        )
        
        self.assertTrue(result)
        call_args = mock_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])
        
        self.assertEqual(stored_data['article_id'], article_id)
        self.assertEqual(stored_data['id'], job_id)
    
    @patch('api.job_queue.get_redis_client')
    def test_article_id_preservation(self, mock_get_redis):
        """Test that article_id is preserved if not provided."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        job_id = "test-job-123"
        existing_article_id = "existing-article-789"
        
        existing_status = {
            'id': job_id,
            'article_id': existing_article_id,
            'status': 'queued',
            'progress': 0
        }
        mock_redis.get.return_value = json.dumps(existing_status)
        
        result = update_job_status(
            job_id=job_id,
            status='running',
            progress=50,
            message='Processing...'
        )
        
        self.assertTrue(result)
        call_args = mock_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])
        
        self.assertEqual(stored_data['article_id'], existing_article_id)
    
    @patch('api.job_queue.get_redis_client')
    def test_created_at_preservation(self, mock_get_redis):
        """Test that created_at is preserved across status transitions."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.get.return_value = None
        
        job_id = "test-job-123"
        article_id = "test-article-456"
        
        # Initial queued status
        result1 = update_job_status(
            job_id=job_id,
            status='queued',
            progress=0,
            message='Job queued',
            article_id=article_id
        )
        self.assertTrue(result1)
        
        first_call_args = mock_redis.setex.call_args_list[0]
        first_stored_data = json.loads(first_call_args[0][2])
        created_at = first_stored_data.get('created_at')
        self.assertIsNotNone(created_at)
        
        # Simulate existing data
        existing_status = {
            'id': job_id,
            'article_id': article_id,
            'status': 'queued',
            'progress': 0,
            'created_at': created_at,
            'updated_at': datetime.now().isoformat()
        }
        mock_redis.get.return_value = json.dumps(existing_status)
        
        # Update to running
        result2 = update_job_status(
            job_id=job_id,
            status='running',
            progress=50,
            message='Processing...'
        )
        self.assertTrue(result2)
        
        second_call_args = mock_redis.setex.call_args_list[1]
        second_stored_data = json.loads(second_call_args[0][2])
        
        # Verify created_at preserved
        self.assertEqual(second_stored_data.get('created_at'), created_at)


if __name__ == '__main__':
    unittest.main()

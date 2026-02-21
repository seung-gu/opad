"""Comprehensive tests for Redis queue operations via RedisJobQueueAdapter."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapter.queue.redis_job_queue import RedisJobQueueAdapter
from adapter.fake.job_queue import FakeJobQueueAdapter
from adapter.fake.article_repository import FakeArticleRepository
from worker.processor import process_job
from domain.model.article import Article, ArticleInputs, ArticleStatus
from domain.model.job import JobContext

TEST_INPUTS = ArticleInputs(language='German', level='B2', length='500', topic='AI')


class TestQueueBasics(unittest.TestCase):
    """Basic queue operation tests using FakeJobQueueAdapter."""

    def test_fake_job_lifecycle(self):
        """Test complete job lifecycle with FakeJobQueueAdapter."""
        job_queue = FakeJobQueueAdapter()

        job_id = "test-job-123"
        article_id = "test-article-456"
        inputs = {'language': 'German', 'level': 'B2', 'length': '500', 'topic': 'AI'}

        # Enqueue
        result = job_queue.enqueue(job_id, article_id, inputs)
        self.assertTrue(result)

        # Update status
        job_queue.update_status(
            job_id=job_id,
            status='running',
            progress=50,
            message='Processing...',
        )

        # Get status
        status = job_queue.get_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], 'running')
        self.assertEqual(status['progress'], 50)

        # Dequeue
        ctx = job_queue.dequeue()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.job_id, job_id)

    def test_end_to_end_job_processing(self):
        """Test end-to-end job processing flow."""
        repo = FakeArticleRepository()
        job_queue = FakeJobQueueAdapter()

        article = Article(
            id='e2e-test-article',
            inputs=ArticleInputs(language='German', level='B2', length='500', topic='AI'),
            status=ArticleStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id='test-user-789',
        )
        repo.save(article)

        ctx = JobContext(
            job_id='e2e-test-job',
            article_id='e2e-test-article',
            user_id='test-user-789',
            inputs=TEST_INPUTS,
        )

        mock_generate = MagicMock(return_value=True)

        result = process_job(ctx, repo, job_queue, generate=mock_generate)

        self.assertTrue(result)
        status = job_queue.get_status('e2e-test-job')
        self.assertEqual(status['status'], 'completed')
        self.assertEqual(status['progress'], 100)


class TestRedisAdapter(unittest.TestCase):
    """Test RedisJobQueueAdapter with mocked Redis."""

    def setUp(self):
        self.adapter = RedisJobQueueAdapter()

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_enqueue(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        result = self.adapter.enqueue("job-1", "article-1", {"topic": "AI"})

        self.assertTrue(result)
        mock_redis.rpush.assert_called_once()

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_update_and_get_status(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis
        mock_redis.get.return_value = None

        result = self.adapter.update_status("job-1", "queued", 0, "Queued", article_id="art-1")

        self.assertTrue(result)
        mock_redis.setex.assert_called_once()

        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        self.assertEqual(stored_data['article_id'], 'art-1')
        self.assertEqual(stored_data['id'], 'job-1')

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_article_id_preservation(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        existing_status = {
            'id': 'job-1',
            'article_id': 'existing-article',
            'status': 'queued',
            'progress': 0,
        }
        mock_redis.get.return_value = json.dumps(existing_status)

        self.adapter.update_status("job-1", "running", 50, "Processing...")

        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        self.assertEqual(stored_data['article_id'], 'existing-article')

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_progress_preservation(self, mock_get_client):
        """Test that progress is not reset when new progress is 0."""
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        existing_status = {
            'id': 'job-1',
            'status': 'running',
            'progress': 75,
        }
        mock_redis.get.return_value = json.dumps(existing_status)

        self.adapter.update_status("job-1", "failed", 0, "Error")

        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        self.assertEqual(stored_data['progress'], 75)

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_ping_success(self, mock_get_client):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_get_client.return_value = mock_redis

        self.assertTrue(self.adapter.ping())

    @patch.object(RedisJobQueueAdapter, '_get_client')
    def test_ping_failure(self, mock_get_client):
        mock_get_client.return_value = None

        self.assertFalse(self.adapter.ping())


class TestJobStatusFields(unittest.TestCase):
    """Test job status field storage and preservation using FakeJobQueueAdapter."""

    def test_created_at_set_on_queued(self):
        """Test that created_at is set when status is 'queued'."""
        job_queue = FakeJobQueueAdapter()
        job_queue.update_status("job-1", "queued", 0, "Queued", article_id="art-1")

        status = job_queue.get_status("job-1")
        self.assertIsNotNone(status['created_at'])

    def test_created_at_preserved(self):
        """Test that created_at is preserved across updates."""
        job_queue = FakeJobQueueAdapter()
        job_queue.update_status("job-1", "queued", 0, "Queued")
        created_at = job_queue.get_status("job-1")['created_at']

        job_queue.update_status("job-1", "running", 50, "Running")
        status = job_queue.get_status("job-1")
        self.assertEqual(status['created_at'], created_at)


if __name__ == '__main__':
    unittest.main()

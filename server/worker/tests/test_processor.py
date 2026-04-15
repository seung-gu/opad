"""Unit tests for worker error handling."""

import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worker.processor import process_job
from adapter.fake.article_repository import FakeArticleRepository
from adapter.fake.job_queue import FakeJobQueueAdapter
from domain.model.article import Article, ArticleInputs, ArticleStatus
from domain.model.job import JobContext

TEST_INPUTS = ArticleInputs(language='German', level='B2', length='500', topic='AI')


class TestWorkerErrorHandling(unittest.TestCase):
    """Test error handling in worker processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.job_queue = FakeJobQueueAdapter()
        self.ctx = JobContext(
            job_id='test-job',
            article_id='test-article',
            user_id=None,
            inputs=TEST_INPUTS,
        )
        # Pre-create article in fake repo so it can be found
        from datetime import datetime, timezone
        article = Article(
            id='test-article',
            inputs=ArticleInputs(language='German', level='B2', length='500', topic='AI'),
            status=ArticleStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.repo.save(article)

    def test_missing_generate_fails_job(self):
        """Test that missing generate function fails the job."""
        result = process_job(self.ctx, self.repo, self.job_queue, generate=None)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')

    def test_missing_article_fails_job(self):
        """Test that non-existent article fails the job."""
        mock_generate = MagicMock(return_value=True)
        ctx = JobContext(
            job_id='test-job',
            article_id='non-existent',
            user_id=None,
            inputs=self.ctx.inputs,
        )

        result = process_job(ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')

    def test_generate_exception_fails_job(self):
        """Test that generate exception fails the job."""
        mock_generate = MagicMock(side_effect=Exception(
            "1 validation error for NewsArticleList\n"
            "  Invalid JSON: expected `,` or `}` at line 26 column 3"
        ))

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')
        self.assertIn('AI model returned invalid response', status['message'])

    def test_timeout_error(self):
        """Test timeout error handling."""
        mock_generate = MagicMock(side_effect=Exception("Request timeout after 30 seconds"))

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')
        self.assertIn('timed out', status['message'].lower())

    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        mock_generate = MagicMock(side_effect=Exception("Rate limit exceeded. Status code: 429"))

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')
        self.assertIn('rate limit', status['message'].lower())

    def test_generic_error(self):
        """Test generic error handling."""
        mock_generate = MagicMock(side_effect=ValueError("Some unexpected error"))

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')
        self.assertIn('Job failed', status['message'])

    def test_successful_job(self):
        """Test successful job processing."""
        mock_generate = MagicMock(return_value=True)

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertTrue(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'completed')
        self.assertEqual(status['progress'], 100)

    def test_generate_returns_false_fails_job(self):
        """Test that generate returning False fails the job."""
        mock_generate = MagicMock(return_value=False)

        result = process_job(self.ctx, self.repo, self.job_queue, generate=mock_generate)

        self.assertFalse(result)
        status = self.job_queue.get_status('test-job')
        self.assertEqual(status['status'], 'failed')


if __name__ == '__main__':
    unittest.main()

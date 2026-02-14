"""Unit tests for worker error handling."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
# test_processor.py is at /app/src/worker/tests/test_processor.py
# src is at /app/src, so we go up 3 levels
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worker.processor import process_job
from adapter.fake.article_repository import FakeArticleRepository
from domain.model.article import ArticleInputs, ArticleStatus


class TestWorkerErrorHandling(unittest.TestCase):
    """Test error handling in worker processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.job_data = {
            'job_id': 'test-job',
            'article_id': 'test-article',
            'inputs': {
                'language': 'German',
                'level': 'B2',
                'length': '500',
                'topic': 'AI'
            }
        }
        # Pre-create article in fake repo so save_content can find it
        self.repo.save_metadata(
            article_id='test-article',
            inputs=ArticleInputs(language='German', level='B2', length='500', topic='AI'),
        )

    def _get_status_call_args(self, mock_update_status):
        """Extract status call arguments.

        update_job_status is called with positional args:
        update_job_status(job_id, status, progress, message, error, article_id)
                          args[0] args[1] args[2]  args[3]  args[4] args[5]
        """
        args, kwargs = mock_update_status.call_args
        return {
            'job_id': args[0],
            'status': args[1],
            'progress': args[2],
            'message': args[3],
            'error': args[4] if len(args) > 4 else None,
            'article_id': args[5] if len(args) > 5 else None,
        }

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_json_parsing_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test JSON parsing error handling."""
        mock_run_crew.side_effect = Exception(
            "1 validation error for NewsArticleList\n"
            "  Invalid JSON: expected `,` or `}` at line 26 column 3"
        )

        result = process_job(self.job_data, self.repo)

        self.assertFalse(result)
        mock_update_status.assert_called()
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'failed')
        self.assertIn('AI model returned invalid response', call['message'])
        self.assertIn('Invalid JSON', call['error'])

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_timeout_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test timeout error handling."""
        mock_run_crew.side_effect = Exception("Request timeout after 30 seconds")

        result = process_job(self.job_data, self.repo)

        self.assertFalse(result)
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'failed')
        self.assertIn('timed out', call['message'].lower())
        self.assertIn('timeout', call['error'].lower())

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_rate_limit_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test rate limit error handling."""
        mock_run_crew.side_effect = Exception("Rate limit exceeded. Status code: 429")

        result = process_job(self.job_data, self.repo)

        self.assertFalse(result)
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'failed')
        self.assertIn('rate limit', call['message'].lower())
        self.assertIn('429', call['error'])

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_generic_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test generic error handling."""
        mock_run_crew.side_effect = ValueError("Some unexpected error")

        result = process_job(self.job_data, self.repo)

        self.assertFalse(result)
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'failed')
        self.assertIn('Job failed', call['message'])
        self.assertIn('ValueError', call['error'])

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_successful_job(self, mock_listener, mock_run_crew, mock_update_status):
        """Test successful job processing."""
        mock_result = MagicMock()
        mock_result.raw = "# Test Article\n\nContent here"
        mock_result.pydantic.article_content = "# Test Article\n\nContent here"
        mock_result.pydantic.replaced_sentences = []
        mock_run_crew.return_value = mock_result

        mock_listener_instance = MagicMock()
        mock_listener_instance.task_failed = False
        mock_listener.return_value = mock_listener_instance

        result = process_job(self.job_data, self.repo)

        self.assertTrue(result)
        mock_update_status.assert_called()
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'completed')
        self.assertEqual(call['progress'], 100)
        self.assertEqual(call['article_id'], 'test-article')

        # Verify article was saved via FakeRepo
        article = self.repo.get_by_id('test-article')
        self.assertEqual(article.content, "# Test Article\n\nContent here")
        self.assertEqual(article.status, ArticleStatus.COMPLETED)

    @patch('worker.context.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_upload_failure_fails_job(self, mock_listener, mock_run_crew, mock_update_status):
        """Test that save_content failure fails the job."""
        mock_result = MagicMock()
        mock_result.raw = "# Test Article"
        mock_result.pydantic.article_content = "# Test Article"
        mock_result.pydantic.replaced_sentences = []
        mock_run_crew.return_value = mock_result

        mock_listener_instance = MagicMock()
        mock_listener_instance.task_failed = False
        mock_listener.return_value = mock_listener_instance

        # Use a job with non-existent article_id so save_content returns False
        job_data = {**self.job_data, 'article_id': 'non-existent'}
        result = process_job(job_data, self.repo)

        self.assertFalse(result)
        call = self._get_status_call_args(mock_update_status)
        self.assertEqual(call['status'], 'failed')
        self.assertEqual(call['progress'], 0)
        self.assertIn('Failed to save article to database', call['message'])
        self.assertIn('MongoDB save error', call['error'])


class TestTaskProgressMapping(unittest.TestCase):
    """Test task progress mapping constants."""

    def test_task_progress_constants(self):
        """Test that TASK_PROGRESS constants are correct."""
        from utils.progress import TASK_PROGRESS

        self.assertIn('find_news_articles', TASK_PROGRESS)
        self.assertIn('pick_best_article', TASK_PROGRESS)
        self.assertIn('adapt_news_article', TASK_PROGRESS)
        self.assertIn('review_article_quality', TASK_PROGRESS)

        self.assertEqual(TASK_PROGRESS['find_news_articles']['start'], 0)
        self.assertEqual(TASK_PROGRESS['find_news_articles']['end'], 25)
        self.assertEqual(TASK_PROGRESS['review_article_quality']['end'], 95)


if __name__ == '__main__':
    unittest.main()

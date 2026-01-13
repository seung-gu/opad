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


class TestWorkerErrorHandling(unittest.TestCase):
    """Test error handling in worker processor."""
    
    def setUp(self):
        """Set up test fixtures."""
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
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_json_parsing_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test JSON parsing error handling."""
        # Mock run_crew to raise JSON error
        mock_run_crew.side_effect = Exception(
            "1 validation error for NewsArticleList\n"
            "  Invalid JSON: expected `,` or `}` at line 26 column 3"
        )
        
        result = process_job(self.job_data)
        
        # Should return False
        self.assertFalse(result)
        
        # Should call update_job_status with user-friendly message
        mock_update_status.assert_called()
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('AI model returned invalid response', call_args[1]['message'])
        self.assertIn('Invalid JSON', call_args[1]['error'])
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_timeout_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test timeout error handling."""
        mock_run_crew.side_effect = Exception("Request timeout after 30 seconds")
        
        result = process_job(self.job_data)
        
        self.assertFalse(result)
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('timed out', call_args[1]['message'].lower())
        self.assertIn('timeout', call_args[1]['error'].lower())
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_rate_limit_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test rate limit error handling."""
        mock_run_crew.side_effect = Exception("Rate limit exceeded. Status code: 429")
        
        result = process_job(self.job_data)
        
        self.assertFalse(result)
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('rate limit', call_args[1]['message'].lower())
        self.assertIn('429', call_args[1]['error'])
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_generic_error(self, mock_listener, mock_run_crew, mock_update_status):
        """Test generic error handling."""
        mock_run_crew.side_effect = ValueError("Some unexpected error")
        
        result = process_job(self.job_data)
        
        self.assertFalse(result)
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('Job failed', call_args[1]['message'])
        self.assertIn('ValueError', call_args[1]['error'])
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.save_article')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_successful_job(self, mock_listener, mock_run_crew, mock_save_article, mock_update_status):
        """Test successful job processing."""
        # Mock successful execution
        mock_result = MagicMock()
        mock_result.raw = "# Test Article\n\nContent here"
        mock_run_crew.return_value = mock_result
        mock_save_article.return_value = True
        
        # Mock listener instance with task_failed attribute
        mock_listener_instance = MagicMock()
        mock_listener_instance.task_failed = False  # No tasks failed
        mock_listener.return_value = mock_listener_instance
        
        result = process_job(self.job_data)
        
        self.assertTrue(result)
        # Should update status to succeeded
        mock_update_status.assert_called()
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'succeeded')
        self.assertEqual(call_args[1]['progress'], 100)
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.save_article')
    @patch('worker.processor.run_crew')
    @patch('crew.progress_listener.JobProgressListener')
    def test_upload_failure_fails_job(self, mock_listener, mock_run_crew, mock_save_article, mock_update_status):
        """Test that MongoDB save failure fails the job.
        
        Rationale: Without successful save, the generated article content is lost
        (only exists in memory). Users cannot access the content, so marking the job
        as 'succeeded' would be misleading. Save failure = job failure.
        """
        mock_result = MagicMock()
        mock_result.raw = "# Test Article"
        mock_run_crew.return_value = mock_result
        # Mock MongoDB save to return False (failure)
        mock_save_article.return_value = False
        
        # Mock listener instance with task_failed attribute
        mock_listener_instance = MagicMock()
        mock_listener_instance.task_failed = False  # No tasks failed
        mock_listener.return_value = mock_listener_instance
        
        result = process_job(self.job_data)
        
        # Job should fail due to save failure
        self.assertFalse(result)
        
        # Final status should be 'failed' with error message
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertEqual(call_args[1]['progress'], 0)
        self.assertIn('Failed to save article to database', call_args[1]['message'])
        self.assertIn('MongoDB save error', call_args[1]['error'])
        
        # Save should have been attempted
        mock_save_article.assert_called_once_with(
            article_id='test-article',
            content="# Test Article"
        )


class TestTaskProgressMapping(unittest.TestCase):
    """Test task progress mapping constants."""
    
    def test_task_progress_constants(self):
        """Test that TASK_PROGRESS constants are correct."""
        from utils.progress import TASK_PROGRESS
        
        # Verify all tasks are defined
        self.assertIn('find_news_articles', TASK_PROGRESS)
        self.assertIn('pick_best_article', TASK_PROGRESS)
        self.assertIn('adapt_news_article', TASK_PROGRESS)
        self.assertIn('add_vocabulary', TASK_PROGRESS)
        
        # Verify progress ranges
        self.assertEqual(TASK_PROGRESS['find_news_articles']['start'], 0)
        self.assertEqual(TASK_PROGRESS['find_news_articles']['end'], 25)
        self.assertEqual(TASK_PROGRESS['add_vocabulary']['end'], 95)


if __name__ == '__main__':
    unittest.main()

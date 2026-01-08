"""Unit tests for worker error handling."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_json_parsing_error(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
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
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_timeout_error(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
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
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_rate_limit_error(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
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
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_generic_error(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
        """Test generic error handling."""
        mock_run_crew.side_effect = ValueError("Some unexpected error")
        
        result = process_job(self.job_data)
        
        self.assertFalse(result)
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('Job failed', call_args[1]['message'])
        self.assertIn('ValueError', call_args[1]['error'])
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_successful_job(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
        """Test successful job processing."""
        # Mock successful execution
        mock_result = MagicMock()
        mock_result.raw = "# Test Article\n\nContent here"
        mock_run_crew.return_value = mock_result
        mock_upload.return_value = True
        
        result = process_job(self.job_data)
        
        self.assertTrue(result)
        # Should update status to succeeded
        mock_update_status.assert_called()
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'succeeded')
        self.assertEqual(call_args[1]['progress'], 100)
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    def test_upload_failure(self, mock_set_job_id, mock_upload, mock_run_crew, mock_update_status):
        """Test R2 upload failure handling."""
        mock_result = MagicMock()
        mock_result.raw = "# Test Article"
        mock_run_crew.return_value = mock_result
        mock_upload.return_value = False
        
        result = process_job(self.job_data)
        
        self.assertFalse(result)
        call_args = mock_update_status.call_args
        self.assertEqual(call_args[1]['status'], 'failed')
        self.assertIn('Failed to upload', call_args[1]['error'])


if __name__ == '__main__':
    unittest.main()

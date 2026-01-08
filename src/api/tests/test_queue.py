"""Integration tests for worker-queue-redis flow."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.queue import enqueue_job, get_job_status, update_job_status
from worker.processor import process_job


class TestIntegration(unittest.TestCase):
    """Integration tests for job queue flow."""
    
    @patch('api.queue.get_redis_client')
    def test_job_lifecycle(self, mock_get_redis):
        """Test complete job lifecycle: enqueue -> process -> status update."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        # Test enqueue
        job_id = "test-job-123"
        article_id = "test-article-456"
        inputs = {'language': 'German', 'level': 'B2', 'length': '500', 'topic': 'AI'}
        
        result = enqueue_job(job_id, article_id, inputs)
        self.assertTrue(result)
        mock_redis.lpush.assert_called_once()
        
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
    
    @patch('worker.processor.update_job_status')
    @patch('worker.processor.run_crew')
    @patch('worker.processor.upload_to_cloud')
    @patch('utils.progress.set_current_job_id')
    @patch('api.queue.get_redis_client')
    def test_end_to_end_job_processing(self, mock_get_redis, mock_set_job_id, 
                                        mock_upload, mock_run_crew, mock_update_status):
        """Test end-to-end job processing flow."""
        # Setup
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        job_data = {
            'job_id': 'e2e-test-job',
            'article_id': 'e2e-test-article',
            'inputs': {'language': 'German', 'level': 'B2', 'length': '500', 'topic': 'AI'}
        }
        
        # Mock successful execution
        mock_result = MagicMock()
        mock_result.raw = "# Test Article\n\nContent"
        mock_run_crew.return_value = mock_result
        mock_upload.return_value = True
        
        # Execute
        result = process_job(job_data)
        
        # Verify
        self.assertTrue(result)
        # Should update status multiple times: running -> succeeded
        self.assertGreaterEqual(mock_update_status.call_count, 2)
        
        # Check final status update
        final_call = mock_update_status.call_args_list[-1]
        self.assertEqual(final_call[1]['status'], 'succeeded')
        self.assertEqual(final_call[1]['progress'], 100)


if __name__ == '__main__':
    unittest.main()

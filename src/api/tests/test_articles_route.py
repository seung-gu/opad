"""Tests for articles route error handling."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
# test_articles_route.py is at /app/src/api/tests/test_articles_route.py
# src is at /app/src, so we go up 3 levels
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app


class TestArticlesRouteErrorHandling(unittest.TestCase):
    """Test error handling in articles route."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch('api.routes.articles.enqueue_job')
    @patch('api.routes.articles.update_job_status')
    def test_generate_article_fails_when_status_update_fails(self, mock_update_status, mock_enqueue):
        """Test that generate_article fails early when status initialization fails.
        
        This prevents orphaned jobs: if we can't create status, don't enqueue the job.
        Status is created first, so enqueue is never called when status fails.
        """
        # Mock failed status update (happens first now)
        mock_update_status.return_value = False
        
        # Mock article store to have the article
        with patch('api.routes.articles._articles_store', {'test-article-id': {'id': 'test-article-id'}}):
            response = self.client.post(
                "/articles/test-article-id/generate",
                json={
                    "language": "German",
                    "level": "B2",
                    "length": "500",
                    "topic": "AI"
                }
            )
        
        # Should return 503 error, not 200 with job_id
        self.assertEqual(response.status_code, 503)
        self.assertIn("Failed to initialize job status", response.json()["detail"])
        
        # Verify status update was called (happens first)
        mock_update_status.assert_called_once()
        # Verify enqueue was NOT called (we fail before reaching it)
        mock_enqueue.assert_not_called()
    
    @patch('api.routes.articles.enqueue_job')
    @patch('api.routes.articles.update_job_status')
    def test_generate_article_fails_when_enqueue_fails(self, mock_update_status, mock_enqueue):
        """Test that generate_article updates status to 'failed' when enqueue fails.
        
        Status is created first (succeeds), then enqueue fails.
        We update status to 'failed' so client can see the failure.
        """
        # Mock successful status update but failed enqueue
        mock_update_status.return_value = True
        mock_enqueue.return_value = False
        
        # Mock article store to have the article
        with patch('api.routes.articles._articles_store', {'test-article-id': {'id': 'test-article-id'}}):
            response = self.client.post(
                "/articles/test-article-id/generate",
                json={
                    "language": "German",
                    "level": "B2",
                    "length": "500",
                    "topic": "AI"
                }
            )
        
        # Should return 503 error
        self.assertEqual(response.status_code, 503)
        self.assertIn("Failed to enqueue job", response.json()["detail"])
        
        # Verify status update was called twice (initial + failure update)
        self.assertEqual(mock_update_status.call_count, 2)
        # Verify enqueue was called once
        mock_enqueue.assert_called_once()
        
        # Verify second status update sets status to 'failed'
        second_call = mock_update_status.call_args_list[1]
        self.assertEqual(second_call[1]['status'], 'failed')
    
    @patch('api.routes.articles.enqueue_job')
    @patch('api.routes.articles.update_job_status')
    def test_generate_article_succeeds_when_both_succeed(self, mock_update_status, mock_enqueue):
        """Test that generate_article succeeds when both status init and enqueue succeed."""
        # Mock both operations succeeding
        mock_update_status.return_value = True
        mock_enqueue.return_value = True
        
        # Need to mock article store
        with patch('api.routes.articles._articles_store', {'test-article-id': {}}):
            response = self.client.post(
                "/articles/test-article-id/generate",
                json={
                    "language": "German",
                    "level": "B2",
                    "length": "500",
                    "topic": "AI"
                }
            )
        
        # Should return 200 with job_id
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertIn("article_id", data)
        
        # Verify both were called (status first, then enqueue)
        mock_update_status.assert_called_once()
        mock_enqueue.assert_called_once()


if __name__ == '__main__':
    unittest.main()


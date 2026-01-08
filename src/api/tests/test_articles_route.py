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
        """Test that generate_article raises exception when status update fails after successful enqueue."""
        # Mock successful enqueue but failed status update
        mock_enqueue.return_value = True
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
        
        # Verify enqueue was called
        mock_enqueue.assert_called_once()
        # Verify status update was called
        mock_update_status.assert_called_once()
    
    @patch('api.routes.articles.enqueue_job')
    @patch('api.routes.articles.update_job_status')
    def test_generate_article_succeeds_when_both_succeed(self, mock_update_status, mock_enqueue):
        """Test that generate_article succeeds when both enqueue and status update succeed."""
        # Mock both operations succeeding
        mock_enqueue.return_value = True
        mock_update_status.return_value = True
        
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
        
        # Verify both were called
        mock_enqueue.assert_called_once()
        mock_update_status.assert_called_once()


if __name__ == '__main__':
    unittest.main()


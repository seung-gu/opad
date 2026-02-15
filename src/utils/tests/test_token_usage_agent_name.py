"""Unit tests for agent_name handling in token usage tracking.

Tests for:
- agent_name extraction from metadata
- agent_name vs agent_role priority
- Type validation for agent_name (string vs non-string)
- Fallback behavior when agent_name is missing/empty
- Malformed metadata handling
- Integration with save_crew_token_usage and TokenUsageRepository
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

from utils.token_usage import save_crew_token_usage


class TestAgentNameHandling(unittest.TestCase):
    """Test cases for agent_name handling in save_crew_token_usage."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.article_id = "article-456"
        self.job_id = "job-789"

    def test_agent_name_is_saved_when_provided(self):
        """Test that agent_name from metadata is saved to database."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Verify agent_name is in metadata
                self.assertIn('agent_name', call_kwargs['metadata'])
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Article Search')

    def test_agent_role_fallback_when_agent_name_is_none(self):
        """Test that agent_role is used as fallback when agent_name is None."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Article Writer',
                'agent_name': None,
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.01):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Should use agent_role as fallback
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Article Writer')

    def test_agent_name_empty_string_uses_fallback(self):
        """Test that empty string agent_name falls back to agent_role."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Quality Reviewer',
                'agent_name': '',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 75,
                'completion_tokens': 25,
                'total_tokens': 100
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Empty string is falsy, should use agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Quality Reviewer')

    def test_agent_name_with_numeric_value_uses_fallback(self):
        """Test that numeric agent_name is rejected, uses agent_role instead."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 123,  # Non-string value
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Non-string should be rejected by isinstance check
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Researcher')

    def test_agent_name_with_boolean_value_uses_fallback(self):
        """Test that boolean agent_name is rejected, uses agent_role instead."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Content Parser',
                'agent_name': True,  # Boolean value
                'model': 'gpt-4',
                'prompt_tokens': 150,
                'completion_tokens': 75,
                'total_tokens': 225
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Boolean should be rejected
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Content Parser')

    def test_agent_name_with_dict_value_uses_fallback(self):
        """Test that dict agent_name is rejected, uses agent_role instead."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Validator',
                'agent_name': {'name': 'test'},  # Dict value
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Dict should be rejected
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Validator')

    def test_agent_name_with_special_characters(self):
        """Test that agent_name with special characters is preserved."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Reviewer',
                'agent_name': 'Quality Check #2 (Advanced)',
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.01):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Special characters should be preserved
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Quality Check #2 (Advanced)')

    def test_agent_name_with_unicode_characters(self):
        """Test that agent_name with unicode characters is preserved."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Rechercheur',
                'agent_name': 'Recherche 📰 Française',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Unicode should be preserved
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Recherche 📰 Française')

    def test_agent_name_priority_over_agent_role(self):
        """Test that agent_name takes priority over agent_role in metadata."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Long Role Name',
                'agent_name': 'Short Name',
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.01):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # agent_name should be used, not agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Short Name')

    def test_agent_name_with_leading_trailing_whitespace(self):
        """Test that agent_name with whitespace is preserved as-is."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': '  Article Search  ',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Whitespace should be preserved
                self.assertEqual(call_kwargs['metadata']['agent_name'], '  Article Search  ')

    def test_multiple_agents_different_agent_names(self):
        """Test multiple agents with different agent_name values."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Writer',
                'agent_name': None,  # Falls back to agent_role
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            },
            {
                'agent_role': 'Reviewer',
                'agent_name': 'Quality Check',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 75,
                'completion_tokens': 25,
                'total_tokens': 100
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify all 3 calls with correct agent_name values
                self.assertEqual(mock_repo.save.call_count, 3)
                calls = mock_repo.save.call_args_list

                # First agent: agent_name provided
                self.assertEqual(calls[0][1]['metadata']['agent_name'], 'Article Search')

                # Second agent: None falls back to agent_role
                self.assertEqual(calls[1][1]['metadata']['agent_name'], 'Writer')

                # Third agent: agent_name provided
                self.assertEqual(calls[2][1]['metadata']['agent_name'], 'Quality Check')

    def test_agent_name_with_very_long_string(self):
        """Test that very long agent_name is preserved."""
        long_name = 'A' * 500
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': long_name,
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                self.assertEqual(call_kwargs['metadata']['agent_name'], long_name)

    def test_agent_name_metadata_structure(self):
        """Test that agent_name is properly placed in metadata dict."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                metadata = call_kwargs['metadata']

                # Verify metadata has both job_id and agent_name
                self.assertIn('job_id', metadata)
                self.assertIn('agent_name', metadata)
                self.assertEqual(metadata['job_id'], self.job_id)
                self.assertEqual(metadata['agent_name'], 'Article Search')

    def test_agent_name_not_overwriting_job_id(self):
        """Test that agent_name and job_id coexist in metadata."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                metadata = call_kwargs['metadata']

                # Both should exist without overwriting
                self.assertEqual(len(metadata), 2)  # job_id and agent_name
                self.assertEqual(metadata['job_id'], self.job_id)
                self.assertEqual(metadata['agent_name'], 'Article Search')


class TestAgentNameTypeValidation(unittest.TestCase):
    """Test type validation for agent_name field."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.article_id = "article-456"
        self.job_id = "job-789"

    def test_agent_name_type_check_with_string(self):
        """Test that string agent_name passes type check."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # String should pass
                self.assertIsInstance(call_kwargs['metadata']['agent_name'], str)

    def test_agent_name_type_validation_with_list(self):
        """Test that list agent_name is rejected."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': ['Article', 'Search'],  # List instead of string
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Should fall back to agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Researcher')

    def test_agent_name_type_validation_with_none(self):
        """Test that None agent_name is handled correctly."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': None,
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Should fall back to agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Researcher')


if __name__ == '__main__':
    unittest.main()

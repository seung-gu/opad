"""Unit tests for CrewResult class and agent usage tracking.

Tests for:
- CrewResult initialization
- get_agent_usage() with various agent configurations
- Agent name and role extraction
- Token usage metrics collection
- Edge cases: missing LLM, no agents, missing attributes
- Type validation and safe attribute access
"""

import unittest
from unittest.mock import Mock, MagicMock
from crew.main import CrewResult


class TestCrewResultInit(unittest.TestCase):
    """Test cases for CrewResult initialization."""

    def test_crew_result_init_with_valid_result_and_crew(self):
        """Test CrewResult initialization with valid result and crew instance."""
        mock_result = Mock()
        mock_result.raw = "Test output"
        mock_crew = Mock()

        crew_result = CrewResult(mock_result, mock_crew)

        self.assertEqual(crew_result.raw, "Test output")
        self.assertEqual(crew_result.result, mock_result)
        self.assertEqual(crew_result.crew_instance, mock_crew)

    def test_crew_result_init_stores_all_attributes(self):
        """Test that CrewResult stores all passed attributes."""
        mock_result = Mock()
        mock_result.raw = "Sample content"
        mock_crew = Mock()

        crew_result = CrewResult(mock_result, mock_crew)

        # Verify all attributes are stored
        self.assertIsNotNone(crew_result.raw)
        self.assertIsNotNone(crew_result.result)
        self.assertIsNotNone(crew_result.crew_instance)


class TestGetAgentUsage(unittest.TestCase):
    """Test cases for get_agent_usage() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_result = Mock()
        self.mock_result.raw = "Test output"

    def test_get_agent_usage_with_single_agent(self):
        """Test get_agent_usage with single agent."""
        # Create mock agent with LLM
        mock_agent = Mock()
        mock_agent.role = "News Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['agent_role'], 'News Researcher')
        self.assertEqual(usage[0]['agent_name'], 'Article Search')
        self.assertEqual(usage[0]['model'], 'gpt-4.1-mini')
        self.assertEqual(usage[0]['prompt_tokens'], 100)
        self.assertEqual(usage[0]['completion_tokens'], 50)
        self.assertEqual(usage[0]['total_tokens'], 150)
        self.assertEqual(usage[0]['successful_requests'], 1)

    def test_get_agent_usage_with_multiple_agents(self):
        """Test get_agent_usage with multiple agents."""
        # Agent 1
        mock_agent1 = Mock()
        mock_agent1.role = "Researcher"
        mock_agent1.name = "Article Search"
        mock_llm1 = Mock()
        mock_llm1.model = "gpt-4.1-mini"
        mock_usage1 = Mock()
        mock_usage1.prompt_tokens = 100
        mock_usage1.completion_tokens = 50
        mock_usage1.total_tokens = 150
        mock_usage1.successful_requests = 1
        mock_llm1.get_token_usage_summary.return_value = mock_usage1
        mock_agent1.llm = mock_llm1

        # Agent 2
        mock_agent2 = Mock()
        mock_agent2.role = "Writer"
        mock_agent2.name = "Article Selection"
        mock_llm2 = Mock()
        mock_llm2.model = "gpt-4"
        mock_usage2 = Mock()
        mock_usage2.prompt_tokens = 200
        mock_usage2.completion_tokens = 100
        mock_usage2.total_tokens = 300
        mock_usage2.successful_requests = 2
        mock_llm2.get_token_usage_summary.return_value = mock_usage2
        mock_agent2.llm = mock_llm2

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 2)
        # Verify first agent
        self.assertEqual(usage[0]['agent_role'], 'Researcher')
        self.assertEqual(usage[0]['agent_name'], 'Article Search')
        self.assertEqual(usage[0]['model'], 'gpt-4.1-mini')
        # Verify second agent
        self.assertEqual(usage[1]['agent_role'], 'Writer')
        self.assertEqual(usage[1]['agent_name'], 'Article Selection')
        self.assertEqual(usage[1]['model'], 'gpt-4')

    def test_get_agent_usage_agent_name_none(self):
        """Test get_agent_usage when agent has no name (None)."""
        mock_agent = Mock()
        mock_agent.role = "Reviewer"
        mock_agent.name = None  # No name
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 75
        mock_usage.completion_tokens = 25
        mock_usage.total_tokens = 100
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        self.assertIsNone(usage[0]['agent_name'])
        self.assertEqual(usage[0]['agent_role'], 'Reviewer')

    def test_get_agent_usage_agent_without_llm(self):
        """Test get_agent_usage skips agents without LLM."""
        # Agent with LLM
        mock_agent1 = Mock()
        mock_agent1.role = "Researcher"
        mock_agent1.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent1.llm = mock_llm

        # Agent without LLM
        mock_agent2 = Mock()
        mock_agent2.role = "Parser"
        mock_agent2.name = "Content Parser"
        mock_agent2.llm = None  # No LLM

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Should only have one agent (the one with LLM)
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['agent_role'], 'Researcher')

    def test_get_agent_usage_agent_without_llm_attribute(self):
        """Test get_agent_usage skips agents that don't have llm attribute."""
        # Agent with LLM
        mock_agent1 = Mock()
        mock_agent1.role = "Researcher"
        mock_agent1.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent1.llm = mock_llm

        # Agent without llm attribute (simulate by raising AttributeError)
        mock_agent2 = Mock(spec=['role', 'name'])
        mock_agent2.role = "Parser"
        mock_agent2.name = "Content Parser"

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Should only have one agent
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['agent_role'], 'Researcher')

    def test_get_agent_usage_with_empty_agent_list(self):
        """Test get_agent_usage with empty agent list."""
        mock_crew = Mock()
        mock_crew.agents = []

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 0)
        self.assertEqual(usage, [])

    def test_get_agent_usage_with_none_agents(self):
        """Test get_agent_usage when agents is None."""
        mock_crew = Mock()
        mock_crew.agents = None

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Should handle gracefully and return empty list
        self.assertEqual(len(usage), 0)
        self.assertEqual(usage, [])

    def test_get_agent_usage_missing_role_attribute(self):
        """Test get_agent_usage with agent missing role attribute."""
        mock_agent = Mock(spec=['name', 'llm'])
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        # Should use 'unknown' default for missing role
        self.assertEqual(usage[0]['agent_role'], 'unknown')
        self.assertEqual(usage[0]['agent_name'], 'Article Search')

    def test_get_agent_usage_missing_model_attribute(self):
        """Test get_agent_usage with LLM missing model attribute."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock(spec=['get_token_usage_summary'])
        # No model attribute
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        # Should use 'unknown' default for missing model
        self.assertEqual(usage[0]['model'], 'unknown')

    def test_get_agent_usage_missing_token_attributes(self):
        """Test get_agent_usage with token usage missing attributes."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        # Mock usage with missing attributes
        mock_usage = Mock(spec=[])
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        # Should use 0 defaults for missing token attributes
        self.assertEqual(usage[0]['prompt_tokens'], 0)
        self.assertEqual(usage[0]['completion_tokens'], 0)
        self.assertEqual(usage[0]['total_tokens'], 0)
        self.assertEqual(usage[0]['successful_requests'], 0)

    def test_get_agent_usage_with_zero_tokens(self):
        """Test get_agent_usage when agent has zero tokens."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 0
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 0
        mock_usage.successful_requests = 0
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['prompt_tokens'], 0)
        self.assertEqual(usage[0]['completion_tokens'], 0)
        self.assertEqual(usage[0]['total_tokens'], 0)

    def test_get_agent_usage_with_large_token_counts(self):
        """Test get_agent_usage with very large token counts."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100000
        mock_usage.completion_tokens = 50000
        mock_usage.total_tokens = 150000
        mock_usage.successful_requests = 10
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['prompt_tokens'], 100000)
        self.assertEqual(usage[0]['completion_tokens'], 50000)
        self.assertEqual(usage[0]['total_tokens'], 150000)

    def test_get_agent_usage_all_agents_without_llm(self):
        """Test get_agent_usage when all agents lack LLM."""
        mock_agent1 = Mock()
        mock_agent1.role = "Parser"
        mock_agent1.name = "Content Parser"
        mock_agent1.llm = None

        mock_agent2 = Mock()
        mock_agent2.role = "Validator"
        mock_agent2.name = "Content Validator"
        mock_agent2.llm = None

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Should return empty list
        self.assertEqual(len(usage), 0)
        self.assertEqual(usage, [])

    def test_get_agent_usage_mixed_agents_with_and_without_llm(self):
        """Test get_agent_usage with mix of agents with and without LLM."""
        # Agent 1: with LLM
        mock_agent1 = Mock()
        mock_agent1.role = "Researcher"
        mock_agent1.name = "Article Search"
        mock_llm1 = Mock()
        mock_llm1.model = "gpt-4.1-mini"
        mock_usage1 = Mock()
        mock_usage1.prompt_tokens = 100
        mock_usage1.completion_tokens = 50
        mock_usage1.total_tokens = 150
        mock_usage1.successful_requests = 1
        mock_llm1.get_token_usage_summary.return_value = mock_usage1
        mock_agent1.llm = mock_llm1

        # Agent 2: without LLM
        mock_agent2 = Mock()
        mock_agent2.role = "Parser"
        mock_agent2.name = "Content Parser"
        mock_agent2.llm = None

        # Agent 3: with LLM
        mock_agent3 = Mock()
        mock_agent3.role = "Writer"
        mock_agent3.name = "Article Selection"
        mock_llm3 = Mock()
        mock_llm3.model = "gpt-4"
        mock_usage3 = Mock()
        mock_usage3.prompt_tokens = 200
        mock_usage3.completion_tokens = 100
        mock_usage3.total_tokens = 300
        mock_usage3.successful_requests = 2
        mock_llm3.get_token_usage_summary.return_value = mock_usage3
        mock_agent3.llm = mock_llm3

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2, mock_agent3]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Should only have 2 agents (skipped the one without LLM)
        self.assertEqual(len(usage), 2)
        self.assertEqual(usage[0]['agent_role'], 'Researcher')
        self.assertEqual(usage[1]['agent_role'], 'Writer')

    def test_get_agent_usage_preserves_agent_name_value(self):
        """Test that agent_name value is preserved as-is (including None)."""
        # Agent with None name
        mock_agent1 = Mock()
        mock_agent1.role = "Researcher"
        mock_agent1.name = None
        mock_llm1 = Mock()
        mock_llm1.model = "gpt-4.1-mini"
        mock_usage1 = Mock()
        mock_usage1.prompt_tokens = 100
        mock_usage1.completion_tokens = 50
        mock_usage1.total_tokens = 150
        mock_usage1.successful_requests = 1
        mock_llm1.get_token_usage_summary.return_value = mock_usage1
        mock_agent1.llm = mock_llm1

        # Agent with specific name
        mock_agent2 = Mock()
        mock_agent2.role = "Writer"
        mock_agent2.name = "Article Rewrite"
        mock_llm2 = Mock()
        mock_llm2.model = "gpt-4"
        mock_usage2 = Mock()
        mock_usage2.prompt_tokens = 200
        mock_usage2.completion_tokens = 100
        mock_usage2.total_tokens = 300
        mock_usage2.successful_requests = 2
        mock_llm2.get_token_usage_summary.return_value = mock_usage2
        mock_agent2.llm = mock_llm2

        mock_crew = Mock()
        mock_crew.agents = [mock_agent1, mock_agent2]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # First should have None name
        self.assertIsNone(usage[0]['agent_name'])
        # Second should have specific name
        self.assertEqual(usage[1]['agent_name'], "Article Rewrite")

    def test_get_agent_usage_structure_consistency(self):
        """Test that get_agent_usage returns consistent dict structure."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(self.mock_result, mock_crew)
        usage = crew_result.get_agent_usage()

        # Verify dict has expected keys
        expected_keys = {
            'agent_role', 'agent_name', 'model',
            'prompt_tokens', 'completion_tokens', 'total_tokens',
            'successful_requests'
        }
        self.assertEqual(set(usage[0].keys()), expected_keys)


class TestCrewResultIntegration(unittest.TestCase):
    """Integration tests for CrewResult."""

    def test_crew_result_multiple_calls_to_get_agent_usage(self):
        """Test that multiple calls to get_agent_usage return consistent results."""
        mock_agent = Mock()
        mock_agent.role = "Researcher"
        mock_agent.name = "Article Search"
        mock_llm = Mock()
        mock_llm.model = "gpt-4.1-mini"
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.successful_requests = 1
        mock_llm.get_token_usage_summary.return_value = mock_usage
        mock_agent.llm = mock_llm

        mock_result = Mock()
        mock_result.raw = "Test output"
        mock_crew = Mock()
        mock_crew.agents = [mock_agent]

        crew_result = CrewResult(mock_result, mock_crew)

        # Call multiple times
        usage1 = crew_result.get_agent_usage()
        usage2 = crew_result.get_agent_usage()

        # Should return consistent results
        self.assertEqual(usage1, usage2)
        self.assertEqual(len(usage1), 1)
        self.assertEqual(usage1[0]['agent_role'], 'Researcher')


if __name__ == '__main__':
    unittest.main()

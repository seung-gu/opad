#!/usr/bin/env python
import sys
import warnings
import logging
from pathlib import Path

import yaml

# Add src to path for imports when running standalone
_src_path = Path(__file__).parent.parent
sys.path.insert(0, str(_src_path))

from crew.crew import ReadingMaterialCreator
from utils.logging import setup_structured_logging

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Set up structured JSON logging (when running standalone)
# When called from worker, logging is already configured
if __name__ == "__main__":
    setup_structured_logging()

logger = logging.getLogger(__name__)


def _load_agent_names() -> dict[str, str]:
    """Load agent display names from agents.yaml (role -> name mapping)."""
    yaml_path = Path(__file__).parent / "config" / "agents.yaml"
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    # Build role -> name mapping (normalize role by stripping whitespace)
    return {
        agent['role'].strip(): agent['name']
        for agent in config.values()
        if 'role' in agent and 'name' in agent
    }


# Load once at module level
_AGENT_NAMES = _load_agent_names()


class CrewResult:
    """Container for crew execution result and usage metrics."""

    def __init__(self, result, crew_instance):
        self.raw = result.raw
        self.result = result
        self.crew_instance = crew_instance

    def get_agent_usage(self) -> list[dict]:
        """Get token usage per agent with model info.

        Returns:
            List of dicts with agent_role, model, prompt_tokens, completion_tokens, total_tokens
        """
        usage_list = []
        for agent in self.crew_instance.agents:
            # Skip agents without LLM configured
            if not hasattr(agent, 'llm') or agent.llm is None:
                continue

            model = getattr(agent.llm, 'model', 'unknown')
            agent_role = getattr(agent, 'role', 'unknown')
            agent_name = _AGENT_NAMES.get(agent_role.strip())  # Display name from agents.yaml

            # Safely get usage metrics with defaults
            usage = agent.llm.get_token_usage_summary()
            usage_list.append({
                'agent_role': agent_role,
                'agent_name': agent_name,
                'model': model,
                'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(usage, 'completion_tokens', 0),
                'total_tokens': getattr(usage, 'total_tokens', 0),
                'successful_requests': getattr(usage, 'successful_requests', 0)
            })
        return usage_list


def run(inputs):
    """
    Run the reading material creator crew.

    This function simply executes CrewAI and returns the result.
    Progress tracking is handled by JobProgressListener in worker/processor.py
    when called through the worker service.

    Args:
        inputs: Dictionary with:
            - language: Target language for the article
            - level: Language proficiency level (A1-C2)
            - length: Target word count
            - topic: Article topic/subject
            - vocabulary_list: (Optional) List of vocabulary words to incorporate

    Returns:
        CrewResult: Result container with raw output and agent usage metrics
    """

    try:
        logger.info("Starting crew execution...")

        # Create crew instance
        crew_instance = ReadingMaterialCreator().crew()

        # Execute crew - tasks will run sequentially
        # Note: If JobProgressListener was created elsewhere (e.g., in worker/processor.py),
        # it will automatically catch TaskStartedEvent/TaskCompletedEvent via global event bus
        result = crew_instance.kickoff(inputs=inputs)

        logger.info("=== READING MATERIAL CREATED ===")

        return CrewResult(result, crew_instance)
    except Exception as e:
        logger.error(f"An error occurred while running the crew: {e}")
        raise

if __name__ == "__main__":
    inputs = {
        'language': 'German',
        'level': 'B2',
        'length': '500',
        'topic': 'Estimation of group A in football World-Cup 2026'
    }
    run(inputs)
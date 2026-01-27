#!/usr/bin/env python
import sys
import warnings
import logging
from pathlib import Path

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
        CrewOutput: Result from crew execution
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
        
        return result
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
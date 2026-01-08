#!/usr/bin/env python
import sys
import warnings
import json
import logging
from pathlib import Path

from opad.crew import ReadingMaterialCreator

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run(inputs=None):
    """
    Run the reading material creator crew.
    
    This function simply executes CrewAI and returns the result.
    Progress tracking is handled by JobProgressListener in worker/processor.py
    when called through the worker service.
    
    Args:
        inputs: Dictionary with language, level, length, topic.
                If None, reads from input.json file or uses defaults.
    
    Returns:
        CrewOutput: Result from crew execution
    """
    if inputs is None:
        # Try to read from input.json file
        input_file = Path('input.json')
        if input_file.exists():
            with open(input_file, 'r') as f:
                inputs = json.load(f)
        else:
            # Default values
            inputs = {
                'language': 'German',
                'level': 'B2',
                'length': '500',
                'topic': 'Estimation of group A in football World-Cup 2026'
            }

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
    run()
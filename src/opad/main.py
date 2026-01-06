#!/usr/bin/env python
import sys
import warnings
import json
import logging
from pathlib import Path

from datetime import datetime

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
    
    Args:
        inputs: Dictionary with language, level, length, topic.
                If None, reads from input.json file or uses defaults.
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
        result = ReadingMaterialCreator().crew().kickoff(inputs=inputs)
        logger.info("=== READING MATERIAL CREATED ===")
        # Log result.raw line by line to avoid formatting issues in Railway logs
        for line in result.raw.split('\n'):
            logger.info(line)
        
        # Upload to R2
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.cloudflare import upload_to_cloud
            logger.info("Uploading to R2...")
            upload_to_cloud(result.raw)
            logger.info("Successfully uploaded to R2")
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
        
        return result
    except Exception as e:
        logger.error(f"An error occurred while running the crew: {e}")
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == "__main__":
    run()
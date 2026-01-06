#!/usr/bin/env python
import sys
import warnings
import json
import logging
import time
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
        start_time = time.time()
        logger.info("Starting crew execution...")
        
        # Create crew instance
        crew_instance = ReadingMaterialCreator().crew()
        
        # Measure total execution time
        result = crew_instance.kickoff(inputs=inputs)
        total_time = time.time() - start_time
        
        logger.info(f"=== CREW EXECUTION COMPLETED ===")
        logger.info(f"Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        
        # Log task execution details
        logger.info("=== TASK EXECUTION SUMMARY ===")
        logger.info("Note: Individual task times are logged by CrewAI verbose mode above.")
        logger.info("Check the verbose logs above for each task's start/end times.")
        logger.info("Expected task order:")
        logger.info("  1. find_news_articles (usually takes longest - SerperDev API calls)")
        logger.info("  2. pick_best_article (evaluates multiple articles)")
        logger.info("  3. adapt_news_article (rewrites long text - usually takes longest)")
        logger.info("  4. add_vocabulary (extracts and formats vocabulary - usually fastest)")
        
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
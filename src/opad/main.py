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
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.progress import update_status, start_task, complete_task
        
        logger.info("Starting crew execution...")
        update_status('initializing', 0, 'running', 'Initializing...')
        
        # Create crew instance
        crew_instance = ReadingMaterialCreator().crew()
        
        # Get task names for progress tracking
        task_names = ['find_news_articles', 'pick_best_article', 'adapt_news_article', 'add_vocabulary']
        
        # Update status before starting first task
        start_task(task_names[0])
        
        # Execute crew - tasks will run sequentially
        result = crew_instance.kickoff(inputs=inputs)
        
        logger.info("=== READING MATERIAL CREATED ===")
        
        # After kickoff completes, all tasks are done
        complete_task(task_names[-1])
        
        # Upload to R2
        start_task('uploading')
        
        try:
            from utils.cloudflare import upload_to_cloud
            logger.info("Uploading to R2...")
            upload_to_cloud(result.raw)
            logger.info("Successfully uploaded to R2")
            update_status('completed', 100, 'completed', 'Article generated successfully!')
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
            update_status('error', 95, 'error', f'Upload failed: {str(e)}')
        
        return result
    except Exception as e:
        logger.error(f"An error occurred while running the crew: {e}")
        try:
            from utils.progress import update_status
            update_status('error', 0, 'error', f'Error: {str(e)}')
        except:
            pass
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == "__main__":
    run()
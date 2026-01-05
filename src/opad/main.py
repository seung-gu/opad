#!/usr/bin/env python
import sys
import warnings
import json
from pathlib import Path

from datetime import datetime

from opad.crew import ReadingMaterialCreator

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


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
        result = ReadingMaterialCreator().crew().kickoff(inputs=inputs)
        print("\n\n=== READING MATERIAL CREATED ===\n\n")
        print(result.raw)
        
        # Upload to R2
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.cloudflare import upload_to_cloud
            upload_to_cloud(result.raw)
        except Exception as e:
            print(f"Failed to upload to R2: {e}")
        
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == "__main__":
    run()
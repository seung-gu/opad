#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from opad.crew import ReadingMaterialCreator

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the reading material creator crew.
    """
    inputs = {
        'language': 'German',
        'level': 'B1',
        'length': '500',
        'topic': 'Estimation of group A in football World-Cup 2026'
    }

    try:
        result = ReadingMaterialCreator().crew().kickoff(inputs=inputs)
        print("\n\n=== READING MATERIAL CREATED ===\n\n")
        print(result.raw)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == "__main__":
    run()
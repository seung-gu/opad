"""Worker service entry point."""

#!/usr/bin/env python
import sys
import logging
from pathlib import Path

# Add src to path
# main.py is at /app/src/worker/main.py
# src is at /app/src, so we go up 2 levels (same as processor.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.processor import run_worker_loop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for worker service."""
    logger.info("Starting OPAD Worker service...")
    logger.info("This service consumes jobs from Redis queue and executes CrewAI")
    
    try:
        run_worker_loop()
    except KeyboardInterrupt:
        logger.info("Worker stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

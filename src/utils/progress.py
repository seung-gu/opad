"""Progress tracking utilities.

This module provides:
1. TASK_PROGRESS: Shared task progress mapping constants
2. Utility functions for task progress queries

Used by:
- crew.progress_listener.JobProgressListener (Event Listener approach)
- Legacy standalone execution (if any)
"""

import logging

logger = logging.getLogger(__name__)

# Task progress mapping (4 tasks = 0-95%, uploading = 95-100%)
TASK_PROGRESS = {
    'find_news_articles': {
        'start': 0,
        'end': 25,
        'label': 'Finding news articles'
    },
    'pick_best_article': {
        'start': 25,
        'end': 50,
        'label': 'Selecting best article'
    },
    'adapt_news_article': {
        'start': 50,
        'end': 75,
        'label': 'Adapting article for learners'
    },
    'add_vocabulary': {
        'start': 75,
        'end': 95,
        'label': 'Adding vocabulary section'
    },
    'uploading': {
        'start': 95,
        'end': 100,
        'label': 'Uploading to R2'
    }
}


def get_task_info(task_name: str):
    """Get task progress information.
    
    Args:
        task_name: Task name (e.g., 'find_news_articles')
        
    Returns:
        Dictionary with start, end, label or None if not found
    """
    return TASK_PROGRESS.get(task_name)


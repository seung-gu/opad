"""Progress tracking utilities for web UI."""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Get project root (assuming this file is in src/utils, go up 2 levels)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
STATUS_FILE = _PROJECT_ROOT / 'status.json'

# Task progress mapping (4 tasks = 0-95%, uploading = 95-100%)
TASK_PROGRESS = {
    'find_news_articles': {'start': 0, 'end': 25, 'label': 'Finding news articles'},
    'pick_best_article': {'start': 25, 'end': 50, 'label': 'Selecting best article'},
    'adapt_news_article': {'start': 50, 'end': 75, 'label': 'Adapting article'},
    'add_vocabulary': {'start': 75, 'end': 95, 'label': 'Adding vocabulary'},
    'uploading': {'start': 95, 'end': 100, 'label': 'Uploading to R2'}
}


def update_status(current_task: str, progress: int, status: str, message: str = ""):
    """Update status file for web progress tracking.
    
    Args:
        current_task: Current task name
        progress: Progress percentage (0-100)
        status: Status ('running', 'completed', 'error')
        message: Status message
    """
    status_data = {
        'current_task': current_task,
        'progress': progress,
        'status': status,
        'message': message,
        'updated_at': datetime.now().isoformat()
    }
    try:
        # Ensure parent directory exists
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        logger.info(f"Updated status: {current_task} - {progress}% - {status} - {message} (file: {STATUS_FILE})")
    except Exception as e:
        logger.error(f"Failed to update status file {STATUS_FILE}: {e}")


def get_task_info(task_name: str):
    """Get task progress information.
    
    Args:
        task_name: Task name
        
    Returns:
        Dictionary with start, end, label or None if not found
    """
    return TASK_PROGRESS.get(task_name)


def start_task(task_name: str):
    """Mark a task as started.
    
    Args:
        task_name: Task name
    """
    task_info = get_task_info(task_name)
    if task_info:
        update_status(task_name, task_info['start'], 'running', task_info['label'])


def complete_task(task_name: str):
    """Mark a task as completed.
    
    Args:
        task_name: Task name
    """
    task_info = get_task_info(task_name)
    if task_info:
        update_status(task_name, task_info['end'], 'running', f'Completed: {task_info["label"]}')


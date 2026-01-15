"""Structured JSON logging configuration."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    # Standard LogRecord attributes that should not be included as extra fields
    _STANDARD_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname',
        'process', 'processName', 'relativeCreated', 'thread', 'threadName',
        'exc_info', 'exc_text', 'stack_info', 'taskName'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields (all non-standard LogRecord attributes)
        # When using logger.info("message", extra={"jobId": "123"}), 
        # Python adds jobId as a direct attribute in record.__dict__
        for key, value in record.__dict__.items():
            if key not in self._STANDARD_ATTRS and not callable(value):
                log_data[key] = value
        
        return json.dumps(log_data)


def setup_structured_logging():
    """Configure structured JSON logging for the application.
    
    This configures all loggers including uvicorn access logs.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
    
    # Configure uvicorn access logger to use structured logging
    # This prevents duplicate access logs in different format
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = [handler]
    uvicorn_access.setLevel(logging.WARNING)  # Reduce access log noise (only log warnings/errors)

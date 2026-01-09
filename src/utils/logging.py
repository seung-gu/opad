"""Structured JSON logging configuration."""

import json
import logging
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
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

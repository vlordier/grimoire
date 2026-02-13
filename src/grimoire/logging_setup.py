"""Structured logging setup with trace context.

Provides logging with trace_id context throughout ingestion pipeline.
"""

import logging
import sys
from typing import Optional
from logging import LogRecord


class TraceContextFilter(logging.Filter):
    """Add trace_id to log records."""
    
    _trace_id: Optional[str] = None
    
    @classmethod
    def set_trace_id(cls, trace_id: Optional[str]) -> None:
        """Set current trace_id for logging context."""
        cls._trace_id = trace_id
    
    def filter(self, record: LogRecord) -> bool:
        """Add trace_id to record."""
        record.trace_id = self._trace_id or "no-trace"
        return True


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup structured logger with trace context.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with trace context
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Format with trace_id
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(trace_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    # Add trace filter
    trace_filter = TraceContextFilter()
    handler.addFilter(trace_filter)
    logger.addFilter(trace_filter)
    
    logger.propagate = False
    return logger


# Default ingestion logger
ingestion_logger = setup_logging("grimoire.ingestion")
storage_logger = setup_logging("grimoire.storage")

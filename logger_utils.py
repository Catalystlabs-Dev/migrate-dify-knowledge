"""
Dify Migration Tool - Logging Utilities

Thread-safe logger implementation for parallel migration operations.
"""

import logging
import threading
from typing import Optional


class ThreadSafeLogger:
    """
    Thread-safe logger wrapper

    Ensures log messages are not interleaved when multiple threads
    are logging simultaneously (e.g., during parallel KB + Workflow migration).

    Uses a threading lock to serialize log calls across threads while
    maintaining performance through minimal locking scope.

    @example
    logger = ThreadSafeLogger(__name__)
    logger.info("Starting migration...")
    logger.error("Migration failed")
    """

    def __init__(self, name: str):
        """
        Initialize thread-safe logger

        @param name - Logger name (typically __name__ of module)
        """
        self._lock = threading.Lock()
        self._logger = logging.getLogger(name)

    def info(self, message: str) -> None:
        """
        Log info-level message in thread-safe manner

        @param message - Message to log
        """
        with self._lock:
            self._logger.info(message)

    def warning(self, message: str) -> None:
        """
        Log warning-level message in thread-safe manner

        @param message - Message to log
        """
        with self._lock:
            self._logger.warning(message)

    def error(self, message: str) -> None:
        """
        Log error-level message in thread-safe manner

        @param message - Message to log
        """
        with self._lock:
            self._logger.error(message)

    def debug(self, message: str) -> None:
        """
        Log debug-level message in thread-safe manner

        @param message - Message to log
        """
        with self._lock:
            self._logger.debug(message)

    def exception(self, message: str, exc_info: bool = True) -> None:
        """
        Log exception with traceback in thread-safe manner

        @param message - Message to log
        @param exc_info - Include exception info (default: True)
        """
        with self._lock:
            self._logger.exception(message, exc_info=exc_info)


def setup_logging(
    log_file: str = 'dify_migration.log',
    level: int = logging.INFO,
    include_thread_name: bool = True
) -> ThreadSafeLogger:
    """
    Configure and return thread-safe logger

    Sets up both file and console logging with appropriate formatting.
    Includes thread name in format for easier debugging of parallel operations.

    @param log_file - Path to log file (default: 'dify_migration.log')
    @param level - Logging level (default: logging.INFO)
    @param include_thread_name - Include thread name in log format
    @returns Configured ThreadSafeLogger instance

    @example
    logger = setup_logging(log_file='my_migration.log', level=logging.DEBUG)
    logger.info("Migration started")
    """
    # Configure format
    if include_thread_name:
        log_format = '%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'

    # Configure handlers
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return ThreadSafeLogger(__name__)


def get_logger(name: Optional[str] = None) -> ThreadSafeLogger:
    """
    Get thread-safe logger instance

    @param name - Logger name (default: __name__)
    @returns ThreadSafeLogger instance

    @example
    logger = get_logger(__name__)
    """
    return ThreadSafeLogger(name or __name__)

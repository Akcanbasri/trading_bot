#!/usr/bin/env python3
"""
Logging configuration module for the trading bot.
Provides a centralized logging setup with console and file handlers.
"""
import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.DEBUG

# Default log directory
DEFAULT_LOG_DIR = "logs"

# Default log file name format
DEFAULT_LOG_FILE_FORMAT = "trading_bot_%Y%m%d_%H%M%S.log"

# Default log rotation settings
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


def setup_logging(
    log_dir=DEFAULT_LOG_DIR,
    log_file_format=DEFAULT_LOG_FILE_FORMAT,
    console_level=DEFAULT_CONSOLE_LEVEL,
    file_level=DEFAULT_FILE_LEVEL,
    log_format=DEFAULT_LOG_FORMAT,
    date_format=DEFAULT_DATE_FORMAT,
    max_bytes=DEFAULT_MAX_BYTES,
    backup_count=DEFAULT_BACKUP_COUNT,
    use_rotating_handler=True,
):
    """
    Configure the logging system for the trading bot.

    Args:
        log_dir: Directory to store log files
        log_file_format: Format for log file names (strftime format)
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_format: Format string for log messages
        date_format: Format string for timestamps
        max_bytes: Maximum size of log file before rotation (for RotatingFileHandler)
        backup_count: Number of backup files to keep (for RotatingFileHandler)
        use_rotating_handler: Whether to use RotatingFileHandler (True) or TimedRotatingFileHandler (False)

    Returns:
        logging.Logger: The configured root logger
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Generate log file name with current timestamp
    log_file_name = datetime.now().strftime(log_file_format)
    log_file_path = log_path / log_file_name

    # Create formatter
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    try:
        if use_rotating_handler:
            # Rotate based on file size
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            # Rotate daily
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
            )

        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Log successful setup
        root_logger.info(f"Logging configured. Log file: {log_file_path}")

    except Exception as e:
        # If file logging setup fails, log to console only
        console_handler.setLevel(logging.ERROR)
        root_logger.error(f"Failed to setup file logging: {e}")
        root_logger.warning("Continuing with console logging only")

    return root_logger


def get_logger(name=None):
    """
    Get a logger instance with the configured settings.

    Args:
        name: Name of the logger (typically __name__ of the calling module)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Example usage
if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test module-specific logger
    module_logger = get_logger(__name__)
    module_logger.info("This is a message from the logger module")

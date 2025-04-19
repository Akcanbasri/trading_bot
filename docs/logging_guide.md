# Trading Bot Logging System Guide

This document provides instructions on how to use the new logging system in the trading bot.

## Overview

The trading bot now uses Python's standard `logging` module with a custom configuration that provides:

1. **Dual Output**: Logs are written to both the console and files
2. **Log Rotation**: Log files are automatically rotated to prevent them from growing too large
3. **Detailed Format**: Log entries include timestamp, log level, module name, function name, line number, and message
4. **Configurable Levels**: Different log levels for console and file output

## Log Format

The default log format is:

```
%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s
```

Example output:
```
2023-04-19 12:34:56.789 | INFO     | src.main:main:119 - Trading bot başlatılıyor...
```

## Using the Logging System

### Basic Usage

In any module where you need logging, add:

```python
import logging

# Get a logger for this module
logger = logging.getLogger(__name__)
```

Then use the logger with appropriate log levels:

```python
logger.debug("Detailed information for debugging")
logger.info("General information about program execution")
logger.warning("Warning messages for potentially problematic situations")
logger.error("Error messages for serious problems")
logger.critical("Critical messages for fatal errors")
```

### Logging with Context

Include relevant context in your log messages:

```python
logger.info(f"Processing {symbol} with timeframe {timeframe}")
logger.error(f"Failed to execute order for {symbol}: {error_message}")
```

### Logging Exceptions

When catching exceptions, include the full traceback:

```python
try:
    # Some code that might raise an exception
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
```

## Configuration

The logging system is configured in `src/utils/logger.py` with the `setup_logging()` function. This function is called at the start of `run_bot.py`.

Default configuration:
- Console: INFO level and above
- File: DEBUG level and above
- Log rotation: 10 MB file size, 5 backup files
- Log directory: `logs/`
- Log file naming: `trading_bot_YYYYMMDD_HHMMSS.log`

## Customizing the Logging System

You can customize the logging system by passing parameters to `setup_logging()`:

```python
from src.utils.logger import setup_logging

# Custom configuration
logger = setup_logging(
    log_dir="custom_logs",
    console_level=logging.WARNING,  # Only show warnings and above in console
    file_level=logging.DEBUG,       # Show all logs in file
    max_bytes=5 * 1024 * 1024,     # 5 MB file size
    backup_count=3                  # Keep 3 backup files
)
```

## Log File Location

Log files are stored in the `logs/` directory by default. Each run of the bot creates a new log file with a timestamp in the filename.

## Troubleshooting

If you encounter issues with the logging system:

1. Check that the `logs/` directory exists and is writable
2. Verify that the bot has permission to write to the directory
3. Check for any error messages in the console output

## Example

See `src/utils/logging_example.py` for a complete example of how to use the logging system. 
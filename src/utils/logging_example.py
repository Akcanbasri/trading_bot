#!/usr/bin/env python3
"""
Example module demonstrating how to use the new logging system.
"""
import logging
import time
import random

# Get a logger for this module
logger = logging.getLogger(__name__)


def example_function():
    """
    Example function demonstrating different log levels.
    """
    logger.debug("This is a debug message - detailed information for debugging")
    logger.info("This is an info message - confirmation that things are working")
    logger.warning("This is a warning message - something unexpected happened")
    logger.error(
        "This is an error message - the software couldn't perform some function"
    )
    logger.critical("This is a critical message - program may be unable to continue")


def process_data(data_size=100):
    """
    Example function demonstrating logging with context.
    """
    logger.info(f"Starting to process {data_size} data points")

    start_time = time.time()

    # Simulate some processing
    for i in range(data_size):
        if i % 10 == 0:
            logger.debug(f"Processing item {i}/{data_size}")

        # Simulate some work
        time.sleep(0.01)

        # Simulate occasional errors
        if random.random() < 0.05:
            logger.warning(f"Encountered issue with item {i}")

    elapsed_time = time.time() - start_time
    logger.info(f"Completed processing {data_size} items in {elapsed_time:.2f} seconds")


def example_with_exception():
    """
    Example function demonstrating exception logging.
    """
    try:
        logger.info("Attempting to perform a risky operation")

        # Simulate an error
        if random.random() < 0.5:
            raise ValueError("Random error occurred")

        logger.info("Operation completed successfully")

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", exc_info=True)
        # exc_info=True includes the full traceback in the log


if __name__ == "__main__":
    # This would be called from run_bot.py in a real scenario
    from src.utils.logger import setup_logging

    # Setup logging
    setup_logging()

    # Run examples
    logger.info("Starting logging examples")
    example_function()
    process_data(50)
    example_with_exception()
    logger.info("Logging examples completed")

#!/usr/bin/env python3
"""
Script to run the trading bot.
"""
import os
import sys
import traceback

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Setup logging first
from src.utils.logger import setup_logging, get_logger

logger = setup_logging()

# Import and run the main function
from main import main

if __name__ == "__main__":
    try:
        logger.info("Starting trading bot...")
        main()
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.critical(f"Trading bot crashed with error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

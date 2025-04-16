"""
Price monitoring script to test real-time price updates.
"""
from datetime import datetime
import time
from loguru import logger
import sys
import os
from dotenv import load_dotenv

from src.api.binance_client import BinanceClient
from src.data.market_data import MarketDataCollector

def monitor_prices(symbol: str = "DOGEUSDT", duration_seconds: int = 60):
    """
    Monitor price changes for a given symbol.
    
    Args:
        symbol: Trading symbol to monitor
        duration_seconds: How long to monitor (in seconds)
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize clients with testnet
    try:
        client = BinanceClient(testnet=True)
        market_data = MarketDataCollector(client)
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        logger.error("Please make sure you have set up your API credentials in the .env file")
        return
    
    logger.info(f"Starting price monitoring for {symbol} for {duration_seconds} seconds...")
    logger.info("Press Ctrl+C to stop early")
    
    start_time = time.time()
    last_price = None
    
    try:
        while time.time() - start_time < duration_seconds:
            current_price = market_data.get_current_price(symbol)
            current_time = datetime.now().strftime("%H:%M:%S")
            
            if last_price is not None:
                price_change = current_price - last_price
                change_percent = (price_change / last_price) * 100
                direction = "↑" if price_change > 0 else "↓" if price_change < 0 else "="
                
                logger.info(f"{current_time} - {symbol}: ${current_price:.8f} {direction} "
                          f"({change_percent:+.4f}%)")
            else:
                logger.info(f"{current_time} - {symbol}: ${current_price:.8f} (initial price)")
            
            last_price = current_price
            time.sleep(1)  # Wait 1 second between updates
            
    except KeyboardInterrupt:
        logger.info("Price monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error during price monitoring: {e}")
    finally:
        logger.info("Price monitoring ended")

if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    # Start monitoring
    monitor_prices() 
"""
Live order execution test module.

This module provides a function to test live order execution capabilities
by opening and closing a minimal position on Binance Futures.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
import statistics

from src.api.client import BinanceClient
from src.utils.notifier import Notifier
from src.utils.notifier import TelegramNotifier

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_server_time_offset(client, is_futures=False):
    """
    Get the time offset between local time and Binance server time.
    Makes multiple attempts to get a stable offset.
    """
    try:
        # Get server time
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        offset = server_time - local_time

        logger.debug(
            f"{'Futures' if is_futures else 'Spot'} Server time offset: {offset}ms"
        )
        return offset
    except Exception as e:
        logger.error(f"Failed to get server time offset: {e}")
        return 0


def get_current_price(client: BinanceClient, symbol: str) -> Optional[float]:
    """Get the current price for a symbol."""
    try:
        logger.debug(f"Getting current price for {symbol}...")
        ticker = client.client.get_symbol_ticker(symbol=symbol)
        price = float(ticker["price"])
        logger.debug(f"Current price for {symbol}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to get current price for {symbol}: {e}")
        return None


def calculate_min_quantity(
    client: BinanceClient, symbol: str, min_notional: float = 5.0
) -> Optional[float]:
    """Calculate the minimum quantity based on current price and minimum notional value."""
    logger.debug(
        f"Calculating minimum quantity for {symbol} with min_notional={min_notional}"
    )
    current_price = get_current_price(client, symbol)
    if not current_price:
        return None

    min_qty = min_notional / current_price

    # Round to the symbol's precision requirements
    try:
        precision = client.get_futures_quantity_precision(symbol)
        min_qty = float(
            Decimal(str(min_qty)).quantize(
                Decimal("0." + "0" * precision), rounding=ROUND_DOWN
            )
        )
        logger.info(
            f"Calculated minimum quantity for {symbol}: {min_qty} at price {current_price} (precision: {precision})"
        )
        return min_qty
    except Exception as e:
        logger.error(f"Error calculating minimum quantity: {e}")
        return None


def send_notification(notifier: Optional[Notifier], message: str) -> None:
    """Send a notification if a notifier is available."""
    if notifier:
        try:
            logger.debug(f"Sending notification: {message}")
            notifier.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")


def run_live_order_test(
    client: BinanceClient,
    symbol: str = "DOGEUSDT",
    leverage: int = 1,
    notifier: Optional[Notifier] = None,
) -> None:
    """Run a live order test with proper error handling and notifications."""
    try:
        logger.info("Starting live order test...")
        if isinstance(notifier, TelegramNotifier):
            notifier.send_message("🚀 Starting live order test...")

        # Get server time offset for spot API
        spot_offset = get_server_time_offset(client)
        logger.info(f"Spot server time offset: {spot_offset}ms")

        # Get server time offset for futures API
        futures_offset = get_server_time_offset(client, is_futures=True)
        logger.info(f"Futures server time offset: {futures_offset}ms")

        # Wait a second before proceeding
        time.sleep(1)

        logger.info(f"Setting leverage to {leverage}x for {symbol}")
        if isinstance(notifier, TelegramNotifier):
            notifier.send_message(f"⚙️ Setting leverage to {leverage}x for {symbol}")

        # Kaldıraç değiştirme
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        logger.debug(f"Leverage set successfully for {symbol}")

        # Calculate minimum quantity
        min_qty = calculate_min_quantity(client, symbol)
        if not min_qty:
            raise ValueError("Failed to calculate minimum quantity")

        # Test LONG position
        logger.info("Testing LONG position...")
        if isinstance(notifier, TelegramNotifier):
            notifier.send_message("📈 Testing LONG position...")

        # Place test order with exact precision
        order_qty = float(
            Decimal(str(min_qty * 1.1)).quantize(
                Decimal("0." + "0" * client.get_futures_quantity_precision(symbol)),
                rounding=ROUND_DOWN,
            )
        )
        logger.info(f"Placing LONG test order for {symbol} with quantity {order_qty}")

        logger.debug(f"Creating futures order: {symbol} BUY {order_qty}")
        long_order = client.futures_create_order(
            symbol=symbol, side="BUY", order_type="MARKET", quantity=order_qty
        )

        long_order_id = long_order["orderId"]
        logger.info(f"LONG test order placed successfully. Order ID: {long_order_id}")

        if isinstance(notifier, TelegramNotifier):
            notifier.send_trade_notification(
                symbol=symbol,
                side="BUY",
                quantity=order_qty,
                order_id=str(long_order_id),
                leverage=leverage,
                is_open=True,
            )

        # Wait a moment before closing
        time.sleep(1)

        # Close LONG position
        logger.info("Closing LONG position...")
        logger.debug(f"Creating futures close order: {symbol} SELL {order_qty}")
        close_long_order = client.futures_create_order(
            symbol=symbol,
            side="SELL",
            order_type="MARKET",
            quantity=order_qty,
            reduce_only=True,
        )

        logger.info(
            f"LONG position closed. Close order ID: {close_long_order['orderId']}"
        )
        if isinstance(notifier, TelegramNotifier):
            notifier.send_trade_notification(
                symbol=symbol,
                side="SELL",
                quantity=order_qty,
                order_id=str(close_long_order["orderId"]),
                leverage=leverage,
                is_open=False,
            )

        # Wait before testing SHORT position
        time.sleep(2)

        # Test SHORT position
        logger.info("Testing SHORT position...")
        if isinstance(notifier, TelegramNotifier):
            notifier.send_message("📉 Testing SHORT position...")

        logger.debug(f"Creating futures order: {symbol} SELL {order_qty}")
        short_order = client.futures_create_order(
            symbol=symbol, side="SELL", order_type="MARKET", quantity=order_qty
        )

        short_order_id = short_order["orderId"]
        logger.info(f"SHORT test order placed successfully. Order ID: {short_order_id}")

        if isinstance(notifier, TelegramNotifier):
            notifier.send_trade_notification(
                symbol=symbol,
                side="SELL",
                quantity=order_qty,
                order_id=str(short_order_id),
                leverage=leverage,
                is_open=True,
            )

        # Wait a moment before closing
        time.sleep(1)

        # Close SHORT position
        logger.info("Closing SHORT position...")
        logger.debug(f"Creating futures close order: {symbol} BUY {order_qty}")
        close_short_order = client.futures_create_order(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=order_qty,
            reduce_only=True,
        )

        logger.info(
            f"SHORT position closed. Close order ID: {close_short_order['orderId']}"
        )
        if isinstance(notifier, TelegramNotifier):
            notifier.send_trade_notification(
                symbol=symbol,
                side="BUY",
                quantity=order_qty,
                order_id=str(close_short_order["orderId"]),
                leverage=leverage,
                is_open=False,
            )

        if isinstance(notifier, TelegramNotifier):
            notifier.send_message("🎉 All tests completed successfully!")

    except Exception as e:
        error_msg = f"❌ Error during live order test: {str(e)}"
        logger.error(error_msg)
        if isinstance(notifier, TelegramNotifier):
            notifier.send_message(error_msg)
        raise


if __name__ == "__main__":
    # Check for API credentials
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    logger.debug(f"API Key exists: {api_key is not None}")
    logger.debug(f"API Secret exists: {api_secret is not None}")
    logger.debug(f"Telegram Token exists: {telegram_token is not None}")
    logger.debug(f"Telegram Chat ID exists: {telegram_chat_id is not None}")

    if not api_key or not api_secret:
        raise ValueError(
            "API credentials not found. Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables."
        )

    # Initialize notifier if Telegram credentials are available
    notifier = None
    if telegram_token and telegram_chat_id:
        try:
            notifier = TelegramNotifier(telegram_token, telegram_chat_id)
            logger.info("Telegram notifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram notifier: {e}")

    logger.warning(
        "WARNING: This script will execute REAL trades on your Binance Futures account!"
    )
    logger.warning("Make sure you understand that this will use REAL funds!")
    logger.warning(
        "You have 5 seconds to cancel (Ctrl+C) if this is not what you want..."
    )
    time.sleep(5)

    client = None
    try:
        # Initialize client with real Binance API
        logger.debug("Initializing Binance client for real trading...")
        client = BinanceClient(api_key=api_key, api_secret=api_secret, testnet=False)
        logger.info("Binance client initialized successfully for real trading")

        # Run the test with real trading
        run_live_order_test(client, notifier=notifier)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

    finally:
        if client:
            try:
                logger.debug("Closing client connection...")
                client.close()
                logger.info("Client connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing client connection: {e}")

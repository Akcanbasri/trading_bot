#!/usr/bin/env python3
"""
Trading bot'un ana modülü.
"""
import os
import sys
import time
import threading
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.order_management.order_executor import OrderExecutor
from src.risk_management.risk_manager import RiskManager
from src.signals.signal_processor import SignalProcessor
from src.strategies.scaled_entry_exit_strategy import ScaledEntryExitStrategy
from src.utils.exceptions import InsufficientDataError
from src.telegram_notifier import TelegramNotifier
from src.utils.log_throttler import LogThrottler
from binance.client import Client

# Load environment variables
load_dotenv()

# Get logger for this module
logger = logging.getLogger(__name__)

# Global değişkenler
running = True

# Initialize log throttler with default 60-second interval
log_throttler = LogThrottler(default_interval=60.0)

# Set custom intervals for specific log types
log_throttler.set_interval("state_snapshot", 60.0)  # State snapshots every 60 seconds
log_throttler.set_interval("signal_change", 30.0)  # Signal changes every 30 seconds
log_throttler.set_interval("price_update", 30.0)  # Price updates every 30 seconds
log_throttler.set_interval("position_update", 60.0)  # Position updates every 60 seconds
log_throttler.set_interval("balance_update", 300.0)  # Balance updates every 5 minutes


def test_api_connection(client: Client) -> bool:
    """
    Test the API connection with Binance.

    Args:
        client: Binance client instance

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Test API connection by getting server time
        client.get_server_time()
        logger.info("API connection test successful")
        return True
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        return False


def signal_processing_loop(
    strategy: ScaledEntryExitStrategy,
    telegram_notifier: TelegramNotifier,
    symbol: str,
    timeframe: str,
) -> None:
    """
    Process signals in a loop.

    Args:
        strategy: Trading strategy instance
        telegram_notifier: TelegramNotifier instance
        symbol: Trading pair symbol
        timeframe: Timeframe for analysis
    """
    # Track the last signal to detect changes
    last_signal_action = "HOLD"
    last_state_snapshot = None

    try:
        while running:
            # Get current price
            current_price = strategy.market_data.get_current_price(symbol)

            # Get indicator values
            macd_values = strategy.get_macd_values(symbol, timeframe)
            rsi_values = strategy.get_rsi_middle_band_values(symbol, timeframe)
            fibo_values = strategy.get_fibobull_pa_values(symbol, timeframe)

            # Get signal from strategy
            signal = strategy.generate_signal(symbol, timeframe)
            current_signal_action = signal.get("action", "HOLD")

            # Check if signal has changed from HOLD to a trade action or vice versa
            signal_changed = (
                last_signal_action == "HOLD" and current_signal_action != "HOLD"
            ) or (last_signal_action != "HOLD" and current_signal_action == "HOLD")

            # Format support and resistance with proper handling of None values
            support = fibo_values.get("sup")
            resistance = fibo_values.get("res")
            support_str = f"{support:.8f}" if support is not None else "None"
            resistance_str = f"{resistance:.8f}" if resistance is not None else "None"

            # Determine position status
            position_status = "None"
            if (
                hasattr(strategy, "position_state")
                and strategy.position_state.get("direction") != "NONE"
            ):
                direction = strategy.position_state.get("direction", "UNKNOWN")
                entry_price = strategy.position_state.get("entry_price", 0.0)
                current_pnl = 0.0

                # Calculate PnL if possible
                if direction == "LONG":
                    current_pnl = (current_price - entry_price) / entry_price * 100
                elif direction == "SHORT":
                    current_pnl = (entry_price - current_price) / entry_price * 100

                position_status = (
                    f"{direction} from {entry_price:.8f} (PnL: {current_pnl:.2f}%)"
                )

            # Create state snapshot
            current_state = {
                "price": current_price,
                "fibo_trend": fibo_values["trend"],
                "rsi_mom": (
                    "Positive"
                    if rsi_values["AL"]
                    else "Negative" if rsi_values["SAT"] else "Neutral"
                ),
                "macd_hist": macd_values["hist"],
                "decision": current_signal_action,
                "position": position_status,
            }

            # Only log state snapshot if it has changed significantly
            state_changed = (
                last_state_snapshot is None
                or abs(last_state_snapshot["price"] - current_state["price"])
                / last_state_snapshot["price"]
                > 0.001  # 0.1% price change
                or last_state_snapshot["fibo_trend"] != current_state["fibo_trend"]
                or last_state_snapshot["rsi_mom"] != current_state["rsi_mom"]
                or last_state_snapshot["decision"] != current_state["decision"]
                or last_state_snapshot["position"] != current_state["position"]
            )

            if state_changed:
                # Create concise routine log message
                routine_log = (
                    f"State Snapshot: Price={current_price:.8f} | "
                    f"Fibo Trend={fibo_values['trend']} | "
                    f"RSI Mom={'Positive' if rsi_values['AL'] else 'Negative' if rsi_values['SAT'] else 'Neutral'} | "
                    f"MACD Hist={macd_values['hist']:.6f} | "
                    f"Decision={current_signal_action} | "
                    f"Position={position_status}"
                )

                # Use throttled logging for state snapshots
                log_throttler.log("state_snapshot", routine_log, level="info")
                last_state_snapshot = current_state

            # Log signal change immediately if detected
            if signal_changed:
                signal_change_log = (
                    f"Signal Change: {last_signal_action} -> {current_signal_action} "
                    f"(Fibo: {'Long' if fibo_values['long_signal'] else 'Short' if fibo_values['short_signal'] else 'Neutral'}, "
                    f"RSI: {'Positive' if rsi_values['AL'] else 'Negative' if rsi_values['SAT'] else 'Neutral'}, "
                    f"MACD: {'Positive' if macd_values['hist'] > 0 else 'Negative'})"
                )
                # Use throttled logging for signal changes
                log_throttler.log("signal_change", signal_change_log, level="info")

            # Update last signal action for next comparison
            last_signal_action = current_signal_action

            # Process signal
            if signal:
                # Log final decision with detailed reasoning for non-HOLD actions
                action = signal.get("action", "UNKNOWN")
                strength = signal.get("strength", "NONE")

                # Only log detailed decision for non-HOLD actions
                if action != "HOLD":
                    decision_log = f"Final Decision for {symbol}: {action} ({strength})"
                    entry_price = signal.get("entry_price", 0.0)
                    stop_loss = signal.get("stop_loss", 0.0)
                    position_size = signal.get("position_size", 0.0)
                    leverage = signal.get("leverage", 1)

                    decision_log += f"\nEntry Details:"
                    decision_log += f"\n  - Entry Price: {entry_price:.8f} USDT"
                    decision_log += f"\n  - Stop Loss: {stop_loss:.8f} USDT"
                    decision_log += f"\n  - Position Size: {position_size:.8f}"
                    decision_log += f"\n  - Leverage: {leverage}x"

                    if "risk_amount" in signal:
                        decision_log += (
                            f"\n  - Risk Amount: {signal['risk_amount']:.8f} USDT"
                        )

                    if "leverage_details" in signal:
                        details = signal["leverage_details"]
                        decision_log += (
                            f"\n  - Notional Size: {details['notional_size']:.8f} USDT"
                        )
                        decision_log += f"\n  - Margin Required: {details['margin_required']:.8f} USDT"
                        decision_log += (
                            f"\n  - Risk per Unit: {details['risk_per_unit']:.8f} USDT"
                        )

                    # Use throttled logging for decision details
                    log_throttler.log("decision", decision_log, level="info")

                # Send signal notification via Telegram
                if signal.get("type") == "ENTRY":
                    telegram_notifier.notify_indicator_signal(
                        symbol=symbol,
                        signal_type=signal.get("direction", "UNKNOWN"),
                        indicator_values=signal.get("indicator_values", {}),
                    )
                elif signal.get("type") == "EXIT":
                    telegram_notifier.notify_exit_signal(
                        symbol=symbol,
                        exit_type=signal.get("exit_type", "UNKNOWN"),
                        pnl=signal.get("pnl", 0.0),
                    )

            # Sleep for a short time to prevent excessive CPU usage
            time.sleep(1)

    except Exception as e:
        logger.error(f"Error in signal processing loop: {str(e)}")
        telegram_notifier.notify_error(f"Signal processing error: {str(e)}")


def main():
    """
    Main function to run the trading bot.
    """
    global running

    try:
        logger.info("Trading bot başlatılıyor...")

        # Initialize Binance client
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        client = Client(api_key, api_secret)

        # Test API connection
        if not test_api_connection(client):
            logger.error("Failed to connect to Binance API. Exiting...")
            return

        # Initialize market data collector
        market_data = MarketDataCollector(client)

        # Initialize Telegram notifier
        telegram_notifier = TelegramNotifier()

        # Send bot started notification
        telegram_notifier.notify_bot_started()

        # Initialize strategy with parameters
        strategy = ScaledEntryExitStrategy(
            market_data=market_data,
            telegram_notifier=telegram_notifier,
            # MACD parameters
            macd_fast_period=12,
            macd_slow_period=26,
            macd_signal_period=9,
            macd_histogram_threshold=0.0,
            # RSI Middle Band parameters
            rsi_period=14,
            rsi_positive_momentum=50.0,
            rsi_negative_momentum=45.0,
            rsi_ema_period=5,
            # FiboBuLL PA parameters
            fibo_left_bars=8,
            fibo_right_bars=8,
            # Position sizing parameters
            tier1_size_percentage=0.4,  # 40% of total position size
            tier2_size_percentage=0.3,  # 30% of total position size
            tier3_size_percentage=0.3,  # 30% of total position size
            # Take profit parameters
            tp1_rr_ratio=1.5,  # Risk/Reward ratio for first take profit
            tp2_rr_ratio=2.5,  # Risk/Reward ratio for second take profit
            # Risk management
            max_risk_per_trade=0.01,  # 1% max risk per trade
            # Leverage parameters
            min_notional_size=5.0,  # Minimum notional size in USDT
            max_leverage=20,  # Maximum allowed leverage
            max_margin_allocation_percent=0.25,  # Maximum percentage of balance to allocate as margin
        )

        # Set trading pair and timeframe
        symbol = "DOGEUSDT"
        timeframe = "1h"

        # Start signal processing loop
        signal_processing_loop(strategy, telegram_notifier, symbol, timeframe)

        logger.info(
            f"Trading bot çalışıyor. Sembol: {symbol}, Zaman dilimi: {timeframe}"
        )
        logger.info("Botu durdurmak için Ctrl+C tuşlarına basın.")

        # Ana döngü
        while running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Kullanıcı tarafından durduruldu.")
                running = False
                break

    except InsufficientDataError as e:
        error_message = f"InsufficientDataError: {str(e)}"
        logger.error(error_message)
        telegram_notifier.notify_error(
            error_message=error_message,
            context="Bot initialization",
            additional_info={"error_type": "InsufficientDataError"},
        )
    except Exception as e:
        error_type = type(e).__name__
        error_message = f"{error_type}: {str(e)}"
        logger.error(error_message)
        telegram_notifier.notify_error(
            error_message=error_message,
            context="Bot main loop",
            additional_info={"error_type": error_type},
        )
    finally:
        logger.info("Trading bot kapatılıyor...")
        running = False
        telegram_notifier.notify_bot_stopped()


if __name__ == "__main__":
    main()

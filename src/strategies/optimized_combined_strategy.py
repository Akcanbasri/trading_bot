"""
Optimized combined strategy module.
Combines FiboBULL PA, RSI Middle Band, and MACD indicators for robust trading signals.
"""

import logging
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector
from src.strategies.fibobull_pa_strategy import FibobullPAStrategy
from src.strategies.rsi_middle_band_strategy import RSIMiddleBandStrategy
from src.strategies.macd_strategy import MACDStrategy
from src.utils.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


class OptimizedCombinedStrategy(BaseStrategy):
    """
    Optimized combined strategy that uses three main indicators:
    1. FiboBULL PA Strategy - For price action and pattern recognition (40% weight)
    2. RSI Middle Band Strategy - For momentum and trend confirmation (30% weight)
    3. MACD Strategy - For trend direction and momentum (30% weight)

    The final signal is generated based on a weighted consensus of all three strategies.
    """

    def __init__(
        self,
        market_data,
        # FiboBULL PA parameters
        fibo_left_bars: int = 8,
        fibo_right_bars: int = 8,
        # RSI Middle Band parameters
        rsi_period: int = 14,
        rsi_positive_momentum: float = 50.0,
        rsi_negative_momentum: float = 45.0,
        rsi_ema_period: int = 20,
        # MACD parameters
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
        macd_histogram_threshold: float = 0.0,
    ):
        """
        Initialize the optimized combined strategy.

        Args:
            market_data: MarketDataCollector instance
            fibo_left_bars: Number of bars to look back for Fibonacci patterns
            fibo_right_bars: Number of bars to look forward for Fibonacci patterns
            rsi_period: Period for RSI calculation
            rsi_positive_momentum: Upper threshold for RSI
            rsi_negative_momentum: Lower threshold for RSI
            rsi_ema_period: Period for EMA calculation
            macd_fast_period: Fast period for MACD
            macd_slow_period: Slow period for MACD
            macd_signal_period: Signal period for MACD
            macd_histogram_threshold: Threshold for MACD histogram
        """
        super().__init__("Optimized Combined Strategy", market_data)

        # Initialize individual strategies
        self.fibo_strategy = FibobullPAStrategy(
            market_data=market_data,
            left_bars=fibo_left_bars,
            right_bars=fibo_right_bars,
        )

        self.rsi_strategy = RSIMiddleBandStrategy(
            market_data=market_data,
            period=rsi_period,
            positive_momentum=rsi_positive_momentum,
            negative_momentum=rsi_negative_momentum,
            ema_period=rsi_ema_period,
        )

        self.macd_strategy = MACDStrategy(
            market_data=market_data,
            fast_period=macd_fast_period,
            slow_period=macd_slow_period,
            signal_period=macd_signal_period,
            histogram_threshold=macd_histogram_threshold,
        )

        # Store parameters
        self.fibo_left_bars = fibo_left_bars
        self.fibo_right_bars = fibo_right_bars
        self.rsi_period = rsi_period
        self.rsi_positive_momentum = rsi_positive_momentum
        self.rsi_negative_momentum = rsi_negative_momentum
        self.rsi_ema_period = rsi_ema_period
        self.macd_fast_period = macd_fast_period
        self.macd_slow_period = macd_slow_period
        self.macd_signal_period = macd_signal_period
        self.macd_histogram_threshold = macd_histogram_threshold

        # Strategy weights
        self.weights = {
            "fibo": 0.4,  # 40% weight for FiboBULL PA
            "rsi": 0.3,  # 30% weight for RSI Middle Band
            "macd": 0.3,  # 30% weight for MACD
        }

        # Minimum signal strength threshold
        self.min_signal_strength = 0.4

        logger.info(
            f"Initialized Optimized Combined Strategy with parameters: "
            f"Fibo({fibo_left_bars}/{fibo_right_bars}), "
            f"RSI({rsi_period}/{rsi_positive_momentum}/{rsi_negative_momentum}/{rsi_ema_period}), "
            f"MACD({macd_fast_period}/{macd_slow_period}/{macd_signal_period}/{macd_histogram_threshold})"
        )

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate a trading signal by combining signals from all three strategies.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dict containing the combined signal and individual strategy signals

        Raises:
            InsufficientDataError: If there is not enough data for analysis
        """
        try:
            # Get fresh current price
            try:
                current_price = self.market_data.get_current_price(symbol)
                logger.debug(f"Fresh price for {symbol}: {current_price}")
            except Exception as e:
                logger.error(f"Failed to get fresh price for {symbol}: {e}")
                raise

            # Get fresh historical data
            try:
                df = self.market_data.get_historical_data(
                    symbol, timeframe, use_cache=False
                )
                if df.empty:
                    logger.warning(f"No data available for {symbol} {timeframe}")
                    raise InsufficientDataError(f"No data for {symbol} {timeframe}")
                logger.debug(
                    f"Got fresh data for {symbol} {timeframe}, rows: {len(df)}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to get historical data for {symbol} {timeframe}: {e}"
                )
                raise

            # Get signals from individual strategies with fresh data
            fibo_signal = self.fibo_strategy.generate_signal(symbol, timeframe)
            rsi_signal = self.rsi_strategy.generate_signal(symbol, timeframe)
            macd_signal = self.macd_strategy.generate_signal(symbol, timeframe)

            # Extract signal directions
            fibo_direction = fibo_signal["signal"]
            rsi_direction = rsi_signal["signal"]
            macd_direction = macd_signal["signal"]

            # Calculate signal strengths
            fibo_strength = fibo_signal.get("strength", 0.0)
            rsi_strength = rsi_signal.get("strength", 0.0)
            macd_strength = macd_signal.get("strength", 0.0)

            # Combine signals using weighted approach
            signal_weights = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}

            # Add weighted contributions from each strategy
            if fibo_direction == "LONG":
                signal_weights["LONG"] += fibo_strength * self.weights["fibo"]
            elif fibo_direction == "SHORT":
                signal_weights["SHORT"] += fibo_strength * self.weights["fibo"]

            if rsi_direction == "LONG":
                signal_weights["LONG"] += rsi_strength * self.weights["rsi"]
            elif rsi_direction == "SHORT":
                signal_weights["SHORT"] += rsi_strength * self.weights["rsi"]

            if macd_direction == "LONG":
                signal_weights["LONG"] += macd_strength * self.weights["macd"]
            elif macd_direction == "SHORT":
                signal_weights["SHORT"] += macd_strength * self.weights["macd"]

            # Determine final signal
            max_weight = max(signal_weights.values())
            if max_weight >= self.min_signal_strength:
                final_signal = max(signal_weights.items(), key=lambda x: x[1])[0]
                signal_strength = max_weight
            else:
                final_signal = "NEUTRAL"
                signal_strength = 0.0

            # Store the last signal
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": final_signal,
                "strength": signal_strength,
                "current_price": current_price,
                "fibo_signal": fibo_signal,
                "rsi_signal": rsi_signal,
                "macd_signal": macd_signal,
                "weights": signal_weights,
            }

            return self.last_signal

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            raise

    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.

        Returns:
            Dict[str, Any]: Last signal information
        """
        return self.last_signal

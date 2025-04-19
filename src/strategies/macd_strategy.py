"""
MACD Strategy implementation.
This strategy uses Moving Average Convergence Divergence to identify trend changes and momentum.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy implementation.
    Uses Moving Average Convergence Divergence to identify trend changes and momentum.
    """

    def __init__(
        self,
        market_data: MarketDataCollector,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        histogram_threshold: float = 0.0,
        ma_type: str = "EMA",
    ):
        """
        Initialize the MACD strategy.

        Args:
            market_data: MarketDataCollector instance
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            histogram_threshold: Threshold for histogram crossover
            ma_type: Moving average type ("EMA" or "SMA")
        """
        super().__init__("MACD Strategy", market_data)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_threshold = histogram_threshold
        self.ma_type = ma_type.upper()
        self.last_signal = None
        self.last_histogram = None

    def calculate_ma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate moving average based on specified type.

        Args:
            data: Price series
            period: MA period

        Returns:
            Series containing MA values
        """
        if self.ma_type == "EMA":
            return data.ewm(span=period, adjust=False).mean()
        else:  # SMA
            return data.rolling(window=period).mean()

    def calculate_macd(
        self, df: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD indicator components.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple containing:
            - MACD line
            - Signal line
            - Histogram
        """
        close = df["close"]

        # Calculate fast and slow MAs
        fast_ma = self.calculate_ma(close, self.fast_period)
        slow_ma = self.calculate_ma(close, self.slow_period)

        # Calculate MACD line
        macd_line = fast_ma - slow_ma

        # Calculate signal line
        signal_line = self.calculate_ma(macd_line, self.signal_period)

        # Calculate histogram
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate trading signals based on MACD strategy.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dictionary containing signal information
        """
        try:
            # Get historical data
            df = self.market_data.get_historical_data(symbol, timeframe)
            if df.empty:
                raise ValueError(f"No data available for {symbol} {timeframe}")

            # Calculate MACD components
            macd_line, signal_line, histogram = self.calculate_macd(df)

            # Get current values
            current_price = df["close"].iloc[-1]
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_hist = histogram.iloc[-1]

            # Get previous values
            prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0

            # Detect crossovers
            rising_to_falling = prev_hist >= 0 and current_hist < 0
            falling_to_rising = prev_hist <= 0 and current_hist > 0

            # Generate trading signals
            signal = "NEUTRAL"
            strength = 0.0

            if falling_to_rising and current_hist > self.histogram_threshold:
                signal = "LONG"
                strength = min(abs(current_hist) / abs(current_macd), 1.0)
            elif rising_to_falling and current_hist < -self.histogram_threshold:
                signal = "SHORT"
                strength = min(abs(current_hist) / abs(current_macd), 1.0)

            # Store the signal
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "macd": current_macd,
                "signal_line": current_signal,
                "histogram": current_hist,
                "rising_to_falling": rising_to_falling,
                "falling_to_rising": falling_to_rising,
            }

            # Update last histogram value
            self.last_histogram = current_hist

            return self.last_signal

        except Exception as e:
            logger.error(f"Error generating MACD signal: {str(e)}")
            raise

    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.

        Returns:
            Dict containing the last signal information
        """
        return self.last_signal

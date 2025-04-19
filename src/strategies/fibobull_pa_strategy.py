"""
FiboBuLL PA Strategy implementation.
This strategy identifies price action patterns using Fibonacci levels and pivot points.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector


class FibobullPAStrategy(BaseStrategy):
    """
    FiboBuLL PA Strategy implementation.
    Identifies price action patterns using Fibonacci levels and pivot points.
    """

    def __init__(
        self,
        market_data: MarketDataCollector,
        left_bars: int = 8,
        right_bars: int = 8,
    ):
        """
        Initialize the FiboBuLL PA strategy.

        Args:
            market_data: MarketDataCollector instance
            left_bars: Number of bars to look back for pattern formation
            right_bars: Number of bars to look forward for pattern confirmation
        """
        super().__init__("FiboBuLL PA Strategy", market_data)
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.last_signal = None

    def find_pivot_points(
        self, df: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Find pivot high and low points in the price data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple containing:
            - Pivot high points
            - Pivot low points
            - Trend direction
        """
        highs = df["high"]
        lows = df["low"]

        # Calculate pivot points
        pivot_high = pd.Series(index=df.index, dtype=float)
        pivot_low = pd.Series(index=df.index, dtype=float)

        for i in range(self.left_bars, len(df) - self.right_bars):
            # Check for pivot high
            if all(
                highs[i] > highs[i - j] for j in range(1, self.left_bars + 1)
            ) and all(highs[i] > highs[i + j] for j in range(1, self.right_bars + 1)):
                pivot_high[i] = highs[i]

            # Check for pivot low
            if all(lows[i] < lows[i - j] for j in range(1, self.left_bars + 1)) and all(
                lows[i] < lows[i + j] for j in range(1, self.right_bars + 1)
            ):
                pivot_low[i] = lows[i]

        # Calculate trend direction
        trend = pd.Series(index=df.index, dtype=float)
        trend[pivot_high.notna()] = 1
        trend[pivot_low.notna()] = -1
        trend = trend.fillna(method="ffill")

        return pivot_high, pivot_low, trend

    def find_pattern_points(
        self, df: pd.DataFrame, pivot_high: pd.Series, pivot_low: pd.Series
    ) -> Dict[str, float]:
        """
        Find the five points (a, b, c, d, e) needed for pattern recognition.

        Args:
            df: DataFrame with OHLCV data
            pivot_high: Series of pivot high points
            pivot_low: Series of pivot low points

        Returns:
            Dictionary containing the five points
        """
        points = {"a": None, "b": None, "c": None, "d": None, "e": None}

        # Get the most recent pivot points
        recent_pivots = pd.concat([pivot_high, pivot_low]).dropna().sort_index()

        if len(recent_pivots) >= 5:
            points["a"] = recent_pivots.iloc[-1]
            points["b"] = recent_pivots.iloc[-2]
            points["c"] = recent_pivots.iloc[-3]
            points["d"] = recent_pivots.iloc[-4]
            points["e"] = recent_pivots.iloc[-5]

        return points

    def identify_patterns(self, points: Dict[str, float]) -> Dict[str, bool]:
        """
        Identify price action patterns based on the five points.

        Args:
            points: Dictionary containing the five points

        Returns:
            Dictionary containing pattern identifications
        """
        patterns = {
            "higher_high": False,
            "lower_low": False,
            "higher_low": False,
            "lower_high": False,
        }

        if all(v is not None for v in points.values()):
            a, b, c, d, e = (
                points["a"],
                points["b"],
                points["c"],
                points["d"],
                points["e"],
            )

            # Higher High (HH)
            patterns["higher_high"] = a > b and a > c and c > b and c > d

            # Lower Low (LL)
            patterns["lower_low"] = a < b and a < c and c < b and c < d

            # Higher Low (HL)
            patterns["higher_low"] = (
                a >= c and (b > c and b > d and d > c and d > e)
            ) or (a < b and a > c and b < d)

            # Lower High (LH)
            patterns["lower_high"] = (
                a <= c and (b < c and b < d and d < c and d < e)
            ) or (a > b and a < c and b > d)

        return patterns

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate trading signals based on FiboBuLL PA patterns.

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

            # Find pivot points and trend
            pivot_high, pivot_low, trend = self.find_pivot_points(df)

            # Find pattern points
            points = self.find_pattern_points(df, pivot_high, pivot_low)

            # Identify patterns
            patterns = self.identify_patterns(points)

            # Generate signals
            current_price = df["close"].iloc[-1]
            current_trend = trend.iloc[-1]
            prev_trend = trend.iloc[-2] if len(trend) > 1 else None

            # Calculate support and resistance levels
            support = points["a"] if patterns["higher_low"] else None
            resistance = points["a"] if patterns["lower_high"] else None

            # Generate trading signals
            long_signal = (
                prev_trend != 1
                and current_trend == 1
                and patterns["lower_high"]
                and current_price > df["close"].iloc[-2]
            )

            short_signal = (
                prev_trend != -1
                and current_trend == -1
                and patterns["higher_low"]
                and current_price < df["close"].iloc[-2]
            )

            # Determine signal direction and strength
            signal = "NEUTRAL"
            strength = 0.0

            if long_signal:
                signal = "LONG"
                strength = 0.8
            elif short_signal:
                signal = "SHORT"
                strength = 0.8

            # Store the signal
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "support": support,
                "resistance": resistance,
                "patterns": patterns,
                "trend": current_trend,
            }

            return self.last_signal

        except Exception as e:
            logger.error(f"Error generating FiboBuLL PA signal: {str(e)}")
            raise

    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.

        Returns:
            Dict containing the last signal information
        """
        return self.last_signal

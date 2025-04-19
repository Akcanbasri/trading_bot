"""
RSI Middle Band Strategy implementation.
This strategy uses RSI with middle band levels to identify momentum shifts.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector


class RSIMiddleBandStrategy(BaseStrategy):
    """
    RSI Middle Band Strategy implementation.
    Uses RSI with middle band levels to identify momentum shifts and generate trading signals.
    """

    def __init__(
        self,
        market_data: MarketDataCollector,
        period: int = 14,
        positive_momentum: float = 50.0,
        negative_momentum: float = 45.0,
        ema_period: int = 5,
    ):
        """
        Initialize the RSI Middle Band strategy.

        Args:
            market_data: MarketDataCollector instance
            period: RSI calculation period
            positive_momentum: Upper threshold for positive momentum
            negative_momentum: Lower threshold for negative momentum
            ema_period: Period for EMA calculation
        """
        super().__init__("RSI Middle Band Strategy", market_data)
        self.period = period
        self.positive_momentum = positive_momentum
        self.negative_momentum = negative_momentum
        self.ema_period = ema_period
        self.last_signal = None
        self.is_long = False
        self.is_short = False

    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate RSI indicator.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Series containing RSI values
        """
        close = df["close"]
        delta = close.diff()

        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        # Calculate RS and RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate EMA indicator.

        Args:
            df: DataFrame with OHLCV data
            period: EMA period

        Returns:
            Series containing EMA values
        """
        return df["close"].ewm(span=period, adjust=False).mean()

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate trading signals based on RSI Middle Band strategy.

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

            # Calculate indicators
            rsi = self.calculate_rsi(df)
            ema = self.calculate_ema(df, self.ema_period)

            # Get current values
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            current_price = df["close"].iloc[-1]
            ema_change = ema.diff().iloc[-1]

            # Check for momentum shifts
            positive_momentum = (
                prev_rsi < self.positive_momentum
                and current_rsi > self.positive_momentum
                and current_rsi > self.negative_momentum
                and ema_change > 0
            )

            negative_momentum = current_rsi < self.negative_momentum and ema_change < 0

            # Update position states
            if positive_momentum:
                self.is_long = True
                self.is_short = False
            elif negative_momentum:
                self.is_long = False
                self.is_short = True

            # Generate trading signals
            signal = "NEUTRAL"
            strength = 0.0

            if self.is_long and not self.is_short:
                signal = "LONG"
                strength = min((current_rsi - self.positive_momentum) / 10, 1.0)
            elif self.is_short and not self.is_long:
                signal = "SHORT"
                strength = min((self.negative_momentum - current_rsi) / 10, 1.0)

            # Store the signal
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "rsi": current_rsi,
                "ema": ema.iloc[-1],
                "is_long": self.is_long,
                "is_short": self.is_short,
                "positive_momentum": positive_momentum,
                "negative_momentum": negative_momentum,
            }

            return self.last_signal

        except Exception as e:
            logger.error(f"Error generating RSI Middle Band signal: {str(e)}")
            raise

    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.

        Returns:
            Dict containing the last signal information
        """
        return self.last_signal

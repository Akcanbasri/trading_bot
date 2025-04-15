"""
Hareketli Ortalama Kesişim (Moving Average Crossover) stratejisi.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import logging

from src.data.market_data import MarketDataCollector
from src.strategies.base_strategy import BaseStrategy
from src.indicators.base_indicator import BaseIndicator
from src.utils.exceptions import InsufficientDataError, CalculationError, StrategyError

logger = logging.getLogger(__name__)

class MovingAverageCrossover(BaseStrategy):
    """
    Hareketli ortalama kesişim stratejisi.
    
    Kısa ve uzun periyotlu hareketli ortalamalar arasındaki kesişimlere dayalı sinyal üretir.
    
    Attributes:
        short_period (int): The period for the short moving average.
        long_period (int): The period for the long moving average.
        signal_threshold (float): The minimum threshold for signal strength to generate a signal.
    """
    
    def __init__(
        self,
        data_collector: MarketDataCollector,
        short_period: int = 10,
        long_period: int = 30,
        signal_threshold: float = 0.002
    ):
        """
        Initialize the MovingAverageCrossover strategy with the specified parameters.
        
        Args:
            data_collector (MarketDataCollector): Market data collector instance
            short_period (int, optional): The period for calculating the short moving average. Defaults to 10.
            long_period (int, optional): The period for calculating the long moving average. Defaults to 30.
            signal_threshold (float, optional): The threshold for determining signal strength. Defaults to 0.002.
            
        Raises:
            ValueError: If short_period is greater than or equal to long_period,
                        or if any of the parameters are non-positive.
        """
        if short_period <= 0 or long_period <= 0:
            raise ValueError("Moving average periods must be positive integers")
        
        if short_period >= long_period:
            raise ValueError("Short period must be less than long period")
        
        if signal_threshold <= 0:
            raise ValueError("Signal threshold must be a positive number")
        
        self.data_collector = data_collector
        self.short_period = short_period
        self.long_period = long_period
        self.signal_threshold = signal_threshold
        
        self.name = f"MA_Cross_{short_period}_{long_period}"
        self.description = f"Moving Average Crossover strategy with {short_period}/{long_period} periods"
        self.required_data_length = long_period + 10  # Add buffer for calculations
        self.last_signal = None
        
        logger.info(f"Initialized {self.name} strategy with short_period={short_period}, "
                   f"long_period={long_period}, signal_threshold={signal_threshold}")
    
    def calculate_moving_averages(self, prices: List[float]) -> Dict[str, List[float]]:
        """
        Calculate the short and long moving averages for the given price data.
        
        Args:
            prices (List[float]): A list of price data points.
            
        Returns:
            Dict[str, List[float]]: A dictionary containing the short and long moving averages.
            
        Raises:
            InsufficientDataError: If there isn't enough price data to calculate the moving averages.
            CalculationError: If there's an error during the calculation process.
        """
        try:
            if len(prices) < self.long_period:
                raise InsufficientDataError(
                    f"Not enough price data to calculate moving averages. "
                    f"Need at least {self.long_period} data points, but got {len(prices)}"
                )
            
            # Convert to numpy array for more efficient calculations
            prices_array = np.array(prices)
            
            # Calculate short moving average
            short_ma = []
            for i in range(len(prices_array) - self.short_period + 1):
                short_ma.append(np.mean(prices_array[i:i + self.short_period]))
            
            # Calculate long moving average
            long_ma = []
            for i in range(len(prices_array) - self.long_period + 1):
                long_ma.append(np.mean(prices_array[i:i + self.long_period]))
            
            # Pad the beginning of the shorter list with None to align the lists
            padding = [None] * (len(short_ma) - len(long_ma))
            aligned_long_ma = padding + long_ma
            
            return {
                "short_ma": short_ma,
                "long_ma": aligned_long_ma
            }
            
        except InsufficientDataError:
            raise
        except Exception as e:
            logger.error(f"Error calculating moving averages: {str(e)}")
            raise CalculationError(f"Failed to calculate moving averages: {str(e)}") from e
    
    def detect_crossover(self, short_ma: List[Optional[float]], long_ma: List[Optional[float]]) -> Optional[str]:
        """
        Detect if a crossover has occurred in the last two valid data points.
        
        Args:
            short_ma (List[Optional[float]]): The short moving average values.
            long_ma (List[Optional[float]]): The long moving average values.
            
        Returns:
            Optional[str]: 'up' for bullish crossover, 'down' for bearish crossover, None for no crossover.
            
        Raises:
            InsufficientDataError: If there aren't enough valid data points to detect a crossover.
        """
        try:
            # Find the last two valid data points
            valid_points = [(s, l) for s, l in zip(short_ma, long_ma) if s is not None and l is not None]
            
            if len(valid_points) < 2:
                raise InsufficientDataError("Not enough valid data points to detect a crossover")
            
            prev_short, prev_long = valid_points[-2]
            current_short, current_long = valid_points[-1]
            
            # Check for crossover
            if prev_short <= prev_long and current_short > current_long:
                return "up"  # Bullish crossover
            elif prev_short >= prev_long and current_short < current_long:
                return "down"  # Bearish crossover
            else:
                return None  # No crossover
                
        except Exception as e:
            logger.error(f"Error detecting crossover: {str(e)}")
            raise CalculationError(f"Failed to detect crossover: {str(e)}") from e
    
    def calculate_signal_strength(self, short_ma: Optional[float], long_ma: Optional[float]) -> float:
        """
        Calculate the signal strength based on the distance between the moving averages.
        
        Args:
            short_ma (Optional[float]): The current short moving average value.
            long_ma (Optional[float]): The current long moving average value.
            
        Returns:
            float: The signal strength, normalized to the signal threshold.
            
        Raises:
            CalculationError: If either moving average is None or if there's a calculation error.
        """
        try:
            if short_ma is None or long_ma is None:
                raise CalculationError("Cannot calculate signal strength with None values")
            
            if long_ma == 0:
                raise CalculationError("Division by zero: long_ma is zero")
            
            # Calculate the percentage difference between the moving averages
            difference = (short_ma - long_ma) / long_ma
            
            # Normalize to the signal threshold
            strength = difference / self.signal_threshold
            
            return strength
            
        except Exception as e:
            logger.error(f"Error calculating signal strength: {str(e)}")
            raise CalculationError(f"Failed to calculate signal strength: {str(e)}") from e
    
    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate a trading signal based on the moving average crossover strategy.
        
        Args:
            symbol (str): The trading symbol.
            timeframe (str): The timeframe of the price data.
            
        Returns:
            Dict[str, Any]: A dictionary containing the signal information.
            
        Raises:
            InsufficientDataError: If there isn't enough price data.
            CalculationError: If there's an error during calculations.
            StrategyError: If the strategy fails to generate a signal.
        """
        try:
            # Get historical data from market data collector
            df = self.data_collector.get_historical_data(symbol, timeframe)
            
            if df.empty:
                raise InsufficientDataError("No historical data available")
            
            # Extract closing prices
            prices = df['close'].values.tolist()
            
            if len(prices) < max(self.short_period, self.long_period):
                raise InsufficientDataError(
                    f"Not enough price data. Need at least {max(self.short_period, self.long_period)} "
                    f"data points, but got {len(prices)}"
                )
            
            # Calculate moving averages
            ma_data = self.calculate_moving_averages(prices)
            short_ma = ma_data["short_ma"]
            long_ma = ma_data["long_ma"]
            
            # Detect crossover
            crossover = self.detect_crossover(short_ma, long_ma)
            
            # Calculate signal strength
            current_short_ma = short_ma[-1]
            current_long_ma = long_ma[-1]
            strength = self.calculate_signal_strength(current_short_ma, current_long_ma)
            
            # Generate signal based on crossover and strength
            signal = "NEUTRAL"
            if crossover == "up" and strength > 0:
                signal = "BUY"
            elif crossover == "down" and strength < 0:
                signal = "SELL"
            
            # Store the signal
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": abs(strength),
                "timestamp": datetime.now().isoformat(),
                "short_ma": current_short_ma,
                "long_ma": current_long_ma,
                "crossover": crossover,
                "current_price": prices[-1]
            }
            
            return self.last_signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            raise StrategyError(f"Failed to generate signal: {str(e)}") from e
    
    def backtest(self, historical_prices: List[float], symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Backtest the strategy using historical price data.
        
        Args:
            historical_prices (List[float]): Historical price data.
            symbol (str): The trading symbol.
            timeframe (str): The timeframe of the price data.
            
        Returns:
            List[Dict[str, Any]]: A list of signal data at each time point.
            
        Raises:
            InsufficientDataError: If there isn't enough price data.
            CalculationError: If there's an error during calculations.
            StrategyError: If the strategy fails during backtesting.
        """
        try:
            min_required_data = self.long_period
            if len(historical_prices) < min_required_data:
                raise InsufficientDataError(
                    f"Insufficient historical data for backtesting. "
                    f"Need at least {min_required_data} data points, but got {len(historical_prices)}"
                )
            
            signals = []
            
            # Ensure we have enough data for initial calculations
            for i in range(min_required_data, len(historical_prices) + 1):
                try:
                    price_window = historical_prices[:i]
                    signal_data = self.generate_signal(symbol, timeframe)
                    signals.append(signal_data)
                except (InsufficientDataError, CalculationError) as e:
                    logger.warning(f"Skipping signal generation at index {i}: {str(e)}")
                    continue
            
            logger.info(f"Completed backtesting for {symbol} ({timeframe}), generated {len(signals)} signals")
            return signals
            
        except Exception as e:
            logger.error(f"Error during backtesting: {str(e)}")
            raise StrategyError(f"Failed to backtest strategy: {str(e)}") from e 
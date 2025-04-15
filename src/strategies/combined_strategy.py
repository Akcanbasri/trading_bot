"""
Birleşik strateji modülü.
Fibobull PA, RSI Middle Band ve MACD stratejilerini birleştirerek daha güvenilir sinyaller üretir.
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

class CombinedStrategy(BaseStrategy):
    """
    Combines multiple trading strategies to generate a more robust trading signal.
    
    This strategy combines:
    1. Fibobull PA Strategy - For price action and pattern recognition
    2. RSI Middle Band Strategy - For momentum and trend confirmation
    3. MACD Strategy - For trend direction and momentum
    
    The final signal is generated based on a weighted consensus of all strategies.
    """
    
    def __init__(
        self,
        market_data,
        fibo_left_bars: int = 8,
        fibo_right_bars: int = 8,
        rsi_period: int = 14,
        rsi_positive_momentum: float = 70.0,
        rsi_negative_momentum: float = 30.0,
        rsi_ema_period: int = 20,
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
        macd_histogram_threshold: float = 0.0
    ):
        """
        Initialize the combined strategy.
        
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
        super().__init__("Combined Strategy", market_data)
        
        # Initialize individual strategies
        self.fibo_strategy = FibobullPAStrategy(
            market_data=market_data,
            left_bars=fibo_left_bars,
            right_bars=fibo_right_bars
        )
        
        self.rsi_strategy = RSIMiddleBandStrategy(
            market_data=market_data,
            period=rsi_period,
            positive_momentum=rsi_positive_momentum,
            negative_momentum=rsi_negative_momentum,
            ema_period=rsi_ema_period
        )
        
        self.macd_strategy = MACDStrategy(
            market_data=market_data,
            fast_period=macd_fast_period,
            slow_period=macd_slow_period,
            signal_period=macd_signal_period,
            histogram_threshold=macd_histogram_threshold
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
        
        logger.info(f"Initialized Combined Strategy with parameters: "
                   f"Fibo({fibo_left_bars}/{fibo_right_bars}), "
                   f"RSI({rsi_period}/{rsi_positive_momentum}/{rsi_negative_momentum}/{rsi_ema_period}), "
                   f"MACD({macd_fast_period}/{macd_slow_period}/{macd_signal_period}/{macd_histogram_threshold})")
    
    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate a trading signal by combining signals from all strategies.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis
            
        Returns:
            Dict containing the combined signal and individual strategy signals
            
        Raises:
            InsufficientDataError: If there is not enough data for analysis
        """
        try:
            # Get signals from individual strategies
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
            
            # Combine signals using weighted voting
            signals = {
                "LONG": 0,
                "SHORT": 0,
                "NEUTRAL": 0
            }
            
            # Add weighted votes
            signals[fibo_direction] += fibo_strength
            signals[rsi_direction] += rsi_strength
            signals[macd_direction] += macd_strength
            
            # Determine final direction
            final_direction = max(signals.items(), key=lambda x: x[1])[0]
            
            # Calculate combined strength
            total_strength = sum(signals.values())
            combined_strength = signals[final_direction] / total_strength if total_strength > 0 else 0.0
            
            # Create combined signal
            combined_signal = {
                "signal": final_direction,
                "strength": combined_strength,
                "timestamp": pd.Timestamp.now(),
                "symbol": symbol,
                "timeframe": timeframe,
                "strategies": {
                    "fibobull": fibo_signal,
                    "rsi": rsi_signal,
                    "macd": macd_signal
                }
            }
            
            # Store the last signal
            self.last_signal = combined_signal
            
            logger.info(f"Generated combined signal: {combined_signal}")
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error generating combined signal: {str(e)}")
            raise
    
    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.
        
        Returns:
            Dict containing the last signal information
        """
        return self.last_signal if hasattr(self, "last_signal") else None 
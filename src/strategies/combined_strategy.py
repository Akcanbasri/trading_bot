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
        
        # Lower the minimum signal strength threshold
        self.min_signal_strength = 0.4  # Changed from default 0.6 to 0.4
        
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
            # Get fresh current price
            try:
                current_price = self.market_data.get_current_price(symbol)
                logger.debug(f"Fresh price for {symbol}: {current_price}")
            except Exception as e:
                logger.error(f"Failed to get fresh price for {symbol}: {e}")
                raise
            
            # Get fresh historical data
            try:
                df = self.market_data.get_historical_data(symbol, timeframe, use_cache=False)
                if df.empty:
                    logger.warning(f"No data available for {symbol} {timeframe}")
                    raise InsufficientDataError(f"No data for {symbol} {timeframe}")
                logger.debug(f"Got fresh data for {symbol} {timeframe}, rows: {len(df)}")
            except Exception as e:
                logger.error(f"Failed to get historical data for {symbol} {timeframe}: {e}")
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
            signal_weights = {
                "LONG": 0,
                "SHORT": 0,
                "NEUTRAL": 0
            }
            
            # Add weighted contributions from each strategy
            if fibo_direction == "LONG":
                signal_weights["LONG"] += fibo_strength * 0.4  # 40% weight
            elif fibo_direction == "SHORT":
                signal_weights["SHORT"] += fibo_strength * 0.4
            
            if rsi_direction == "LONG":
                signal_weights["LONG"] += rsi_strength * 0.3  # 30% weight
            elif rsi_direction == "SHORT":
                signal_weights["SHORT"] += rsi_strength * 0.3
            
            if macd_direction == "LONG":
                signal_weights["LONG"] += macd_strength * 0.3  # 30% weight
            elif macd_direction == "SHORT":
                signal_weights["SHORT"] += macd_strength * 0.3
            
            # Determine final signal
            max_weight = max(signal_weights.values())
            if max_weight > 0:
                final_signal = max(signal_weights.items(), key=lambda x: x[1])[0]
                signal_strength = max_weight
            else:
                final_signal = "NEUTRAL"
                signal_strength = 0.0
            
            # Create combined signal
            combined_signal = {
                "signal": final_signal,
                "strength": signal_strength,
                "timestamp": pd.Timestamp.now(),
                "symbol": symbol,
                "timeframe": timeframe,
                "current_price": current_price,
                "strategies": {
                    "fibobull": fibo_signal,
                    "rsi": rsi_signal,
                    "macd": macd_signal
                }
            }
            
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error generating combined signal: {e}")
            raise
    
    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.
        
        Returns:
            Dict containing the last signal information
        """
        return self.last_signal if hasattr(self, "last_signal") else None 
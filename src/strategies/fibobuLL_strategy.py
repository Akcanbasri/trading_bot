"""
Fibonacci seviyeleri ve fiyat hareketlerine dayalı trading sinyalleri üreten strateji modülü.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector
from src.exceptions.insufficient_data_error import InsufficientDataError

logger = logging.getLogger(__name__)

class FibobullStrategy(BaseStrategy):
    """
    Fibonacci seviyeleri ve fiyat hareketlerine dayalı alım/satım sinyalleri üreten strateji sınıfı.
    Swing noktalarını tespit ederek Fibonacci seviyelerini hesaplar.
    """
    
    def __init__(
        self,
        data_collector: MarketDataCollector,
        lookback_period: int = 100,
        fib_levels: List[float] = None,
        min_swing_points: int = 5
    ):
        """
        Fibobull strateji sınıfının başlatıcı metodu.
        
        Args:
            data_collector: Market veri toplayıcı nesnesi
            lookback_period: Analiz edilecek geçmiş bar sayısı (varsayılan: 100)
            fib_levels: Fibonacci seviyeleri (varsayılan: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1])
            min_swing_points: Minimum swing noktası sayısı (varsayılan: 5)
        """
        super().__init__()
        self.data_collector = data_collector
        self.lookback_period = lookback_period
        self.fib_levels = fib_levels or [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        self.min_swing_points = min_swing_points
        
        logger.info(
            f"FibobullStrategy başlatıldı: lookback_period={lookback_period}, "
            f"fib_levels={self.fib_levels}, min_swing_points={min_swing_points}"
        )
    
    def find_swing_points(self, prices: List[float]) -> Tuple[List[int], List[int]]:
        """
        Fiyat serisindeki swing yüksek ve alçak noktalarını bulur.
        
        Args:
            prices: Kapanış fiyatları listesi
            
        Returns:
            Tuple[List[int], List[int]]: Swing yüksek ve alçak noktalarının indeksleri
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        if len(prices) < 3:
            raise InsufficientDataError("Swing noktaları için en az 3 fiyat gerekli.")
        
        swing_highs = []
        swing_lows = []
        
        for i in range(1, len(prices) - 1):
            # Swing yüksek noktası kontrolü
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                swing_highs.append(i)
            
            # Swing alçak noktası kontrolü
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                swing_lows.append(i)
        
        return swing_highs, swing_lows
    
    def calculate_fibonacci_levels(self, high: float, low: float) -> Dict[float, float]:
        """
        Verilen yüksek ve alçak noktalar arasında Fibonacci seviyelerini hesaplar.
        
        Args:
            high: Yüksek fiyat
            low: Alçak fiyat
            
        Returns:
            Dict[float, float]: Fibonacci seviyeleri ve karşılık gelen fiyatlar
        """
        price_range = high - low
        fib_levels = {}
        
        for level in self.fib_levels:
            fib_price = low + (price_range * level)
            fib_levels[level] = fib_price
        
        return fib_levels
    
    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Verilen sembol ve zaman dilimi için trading sinyali üretir.
        
        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            timeframe: Zaman dilimi (örn. "15m", "1h", "4h", "1d")
            
        Returns:
            Dict[str, Any]: Sinyal bilgilerini içeren sözlük
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        try:
            # Tarihsel verileri al
            df = self.data_collector.get_historical_data(
                symbol, timeframe, limit=self.lookback_period
            )
            
            if df.empty or len(df) < self.lookback_period:
                raise InsufficientDataError(
                    f"{symbol} için yeterli veri yok. "
                    f"En az {self.lookback_period} bar gerekli."
                )
            
            # Kapanış fiyatlarını al
            prices = df["close"].tolist()
            current_price = prices[-1]
            
            # Swing noktalarını bul
            swing_highs, swing_lows = self.find_swing_points(prices)
            
            if len(swing_highs) < self.min_swing_points or len(swing_lows) < self.min_swing_points:
                raise InsufficientDataError(
                    f"Yeterli swing noktası yok. "
                    f"En az {self.min_swing_points} swing noktası gerekli."
                )
            
            # Son swing yüksek ve alçak noktalarını bul
            last_swing_high = max(swing_highs)
            last_swing_low = max(swing_lows)
            
            # Fibonacci seviyelerini hesapla
            if last_swing_high > last_swing_low:
                fib_levels = self.calculate_fibonacci_levels(
                    prices[last_swing_high], prices[last_swing_low]
                )
            else:
                fib_levels = self.calculate_fibonacci_levels(
                    prices[last_swing_low], prices[last_swing_high]
                )
            
            # Sinyal üret
            signal = "NEUTRAL"
            strength = 0.0
            
            # Fiyatın Fibonacci seviyelerine göre konumunu belirle
            for level, price in fib_levels.items():
                if current_price < price:
                    if level <= 0.382:
                        signal = "LONG"
                        strength = 1.0 - (level / 0.382)
                    break
                elif current_price > price and level >= 0.618:
                    signal = "SHORT"
                    strength = (level - 0.618) / (1.0 - 0.618)
            
            # Son sinyali güncelle
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "fib_levels": fib_levels,
                "last_swing_high": prices[last_swing_high],
                "last_swing_low": prices[last_swing_low]
            }
            
            return self.last_signal
            
        except Exception as e:
            logger.error(f"Sinyal üretilirken hata oluştu: {str(e)}")
            raise
    
    def get_last_signal(self) -> Dict[str, Any]:
        """
        Son üretilen sinyali döndürür.
        
        Returns:
            Dict[str, Any]: Son sinyal bilgilerini içeren sözlük
        """
        return self.last_signal 
"""
MACD (Moving Average Convergence Divergence) stratejisi modülü.
MACD indikatörünü kullanarak alım/satım sinyalleri üretir.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..strategies.base_strategy import BaseStrategy
from ..data.market_data import MarketDataCollector
from ..utils.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

class MACDStrategy(BaseStrategy):
    """
    MACD stratejisi sınıfı.
    MACD indikatörünü kullanarak alım/satım sinyalleri üretir.
    """
    
    def __init__(
        self,
        market_data: MarketDataCollector,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        histogram_threshold: float = 0.0,
        min_bars: int = 30
    ):
        """
        MACD stratejisi sınıfının başlatıcı metodu.
        
        Args:
            market_data: Market veri toplayıcı nesnesi
            fast_period: Hızlı EMA periyodu (varsayılan: 12)
            slow_period: Yavaş EMA periyodu (varsayılan: 26)
            signal_period: Sinyal çizgisi periyodu (varsayılan: 9)
            histogram_threshold: Histogram eşik değeri (varsayılan: 0.0)
            min_bars: Minimum gerekli bar sayısı (varsayılan: 30)
        """
        super().__init__(name="macd_strategy", market_data=market_data)
        
        if fast_period <= 0:
            raise ValueError("Hızlı EMA periyodu pozitif olmalıdır")
        if slow_period <= 0:
            raise ValueError("Yavaş EMA periyodu pozitif olmalıdır")
        if signal_period <= 0:
            raise ValueError("Sinyal çizgisi periyodu pozitif olmalıdır")
        if fast_period >= slow_period:
            raise ValueError("Hızlı EMA periyodu yavaş EMA periyodundan küçük olmalıdır")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_threshold = histogram_threshold
        self.min_bars = min_bars
        
        logger.info(
            f"MACDStrategy başlatıldı: fast_period={fast_period}, "
            f"slow_period={slow_period}, signal_period={signal_period}, "
            f"histogram_threshold={histogram_threshold}, min_bars={min_bars}"
        )
    
    def calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """
        Verilen fiyat listesi için MACD değerlerini hesaplar.
        
        Args:
            prices: Kapanış fiyatları listesi
            
        Returns:
            Dict[str, float]: MACD değerlerini içeren sözlük
        """
        if len(prices) < self.slow_period + self.signal_period:
            raise InsufficientDataError(
                f"MACD hesaplaması için en az {self.slow_period + self.signal_period} "
                f"veri noktası gerekli, ancak sadece {len(prices)} veri noktası mevcut"
            )
        
        # Fiyatları pandas Series'e dönüştür
        price_series = pd.Series(prices)
        
        # EMA'ları hesapla
        fast_ema = price_series.ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = price_series.ewm(span=self.slow_period, adjust=False).mean()
        
        # MACD çizgisini hesapla
        macd_line = fast_ema - slow_ema
        
        # Sinyal çizgisini hesapla
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        
        # Histogramı hesapla
        histogram = macd_line - signal_line
        
        return {
            "macd_line": macd_line.iloc[-1],
            "signal_line": signal_line.iloc[-1],
            "histogram": histogram.iloc[-1]
        }
    
    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Verilen sembol ve zaman dilimi için MACD bazlı trading sinyali üretir.
        
        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            timeframe: Zaman dilimi (örn. "15m", "1h", "4h", "1d")
            
        Returns:
            Dict[str, Any]: Sinyal bilgilerini içeren sözlük
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        try:
            # Tarihsel verileri al - use fresh data
            df = self.market_data.get_historical_data(symbol, timeframe, use_cache=False)
            
            if df.empty or len(df) < self.min_bars:
                raise InsufficientDataError(
                    f"{symbol} için yeterli veri yok. En az {self.min_bars} bar gerekli."
                )
            
            # Kapanış fiyatlarını al
            prices = df["close"].tolist()
            
            # MACD değerlerini hesapla
            macd_values = self.calculate_macd(prices)
            
            # Sinyal gücünü hesapla
            signal_strength = abs(macd_values["histogram"]) / abs(macd_values["macd_line"]) if macd_values["macd_line"] != 0 else 0.0
            
            # Sinyal yönünü belirle
            signal = "NEUTRAL"
            if macd_values["histogram"] > self.histogram_threshold and macd_values["macd_line"] > macd_values["signal_line"]:
                signal = "LONG"
            elif macd_values["histogram"] < -self.histogram_threshold and macd_values["macd_line"] < macd_values["signal_line"]:
                signal = "SHORT"
            
            # Son sinyali güncelle
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": signal_strength,
                "macd_line": macd_values["macd_line"],
                "signal_line": macd_values["signal_line"],
                "histogram": macd_values["histogram"],
                "current_price": prices[-1]
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
"""
RSI ve EMA kullanarak trading sinyalleri üreten strateji modülü.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector
from src.utils.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

class RSIMiddleBandStrategy(BaseStrategy):
    """
    RSI ve EMA kullanarak alım/satım sinyalleri üreten strateji sınıfı.
    RSI'ın orta bandı (50) etrafındaki hareketleri analiz eder.
    """
    
    def __init__(
        self,
        market_data: MarketDataCollector,
        period: int = 14,
        positive_momentum: float = 70.0,
        negative_momentum: float = 30.0,
        ema_period: int = 20
    ):
        """
        RSI Middle Band strateji sınıfının başlatıcı metodu.
        
        Args:
            market_data: Market veri toplayıcı nesnesi
            period: RSI hesaplama periyodu (varsayılan: 14)
            positive_momentum: RSI üst eşik değeri (varsayılan: 70.0)
            negative_momentum: RSI alt eşik değeri (varsayılan: 30.0)
            ema_period: EMA hesaplama periyodu (varsayılan: 20)
        """
        name = f"RSI_Middle_Band_{period}_{ema_period}"
        super().__init__(name=name, market_data=market_data)
        
        self.period = period
        self.positive_momentum = positive_momentum
        self.negative_momentum = negative_momentum
        self.ema_period = ema_period
        
        logger.info(
            f"RSIMiddleBandStrategy başlatıldı: period={period}, "
            f"positive_momentum={positive_momentum}, negative_momentum={negative_momentum}, "
            f"ema_period={ema_period}"
        )
    
    def calculate_rsi(self, prices: List[float]) -> float:
        """
        RSI (Relative Strength Index) değerini hesaplar.
        
        Args:
            prices: Kapanış fiyatları listesi
            
        Returns:
            float: Hesaplanan RSI değeri
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        if len(prices) < self.period + 1:
            raise InsufficientDataError(
                f"RSI hesaplaması için en az {self.period + 1} fiyat gerekli."
            )
        
        # Fiyat değişimlerini hesapla
        deltas = np.diff(prices)
        
        # Pozitif ve negatif değişimleri ayır
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # İlk ortalama kazanç ve kayıpları hesapla
        avg_gain = np.mean(gains[:self.period])
        avg_loss = np.mean(losses[:self.period])
        
        # Sonraki değerler için üssel ortalama kullan
        for i in range(self.period, len(deltas)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period
        
        # RSI hesapla
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    def calculate_ema(self, prices: List[float]) -> float:
        """
        EMA (Exponential Moving Average) değerini hesaplar.
        
        Args:
            prices: Kapanış fiyatları listesi
            
        Returns:
            float: Hesaplanan EMA değeri
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        if len(prices) < self.ema_period:
            raise InsufficientDataError(
                f"EMA hesaplaması için en az {self.ema_period} fiyat gerekli."
            )
        
        # EMA hesapla
        ema = pd.Series(prices).ewm(span=self.ema_period, adjust=False).mean()
        return ema.iloc[-1]
    
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
            df = self.market_data.get_historical_data(symbol, timeframe)
            
            if df.empty or len(df) < max(self.period + 1, self.ema_period):
                raise InsufficientDataError(
                    f"{symbol} için yeterli veri yok. "
                    f"En az {max(self.period + 1, self.ema_period)} bar gerekli."
                )
            
            # Kapanış fiyatlarını al
            prices = df["close"].tolist()
            
            # RSI ve EMA değerlerini hesapla
            rsi = self.calculate_rsi(prices)
            ema = self.calculate_ema(prices)
            current_price = prices[-1]
            
            # Sinyal üret
            signal = "NEUTRAL"
            strength = 0.0
            
            # RSI ve EMA'ya göre sinyal belirle
            if rsi < self.negative_momentum and current_price < ema:
                signal = "LONG"
                strength = (self.negative_momentum - rsi) / self.negative_momentum
            elif rsi > self.positive_momentum and current_price > ema:
                signal = "SHORT"
                strength = (rsi - self.positive_momentum) / (100 - self.positive_momentum)
            
            # Son sinyali güncelle
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "rsi": rsi,
                "ema": ema
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
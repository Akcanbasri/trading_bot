"""
Relative Strength Index (RSI) göstergesi.
"""
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import numpy as np
from loguru import logger

from src.indicators.base_indicator import BaseIndicator


class RSI(BaseIndicator):
    """
    Relative Strength Index (RSI) göstergesi hesaplama sınıfı.
    
    RSI, bir varlığın aşırı alım veya aşırı satım durumunda olup olmadığını
    değerlendirmek için kullanılan momentum osilatörüdür.
    """
    
    def __init__(
        self, 
        period: int = 14, 
        overbought: float = 70.0, 
        oversold: float = 30.0,
        column: str = 'close'
    ):
        """
        RSI göstergesini başlatır.
        
        Args:
            period: RSI hesaplama periyodu (varsayılan: 14)
            overbought: Aşırı alım seviyesi (varsayılan: 70.0)
            oversold: Aşırı satım seviyesi (varsayılan: 30.0)
            column: Hesaplama için kullanılacak veri sütunu (varsayılan: 'close')
        """
        params = {
            'period': period,
            'overbought': overbought,
            'oversold': oversold,
            'column': column
        }
        super().__init__(name='RSI', params=params)
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        RSI değerlerini hesaplar.
        
        Args:
            data: İşlem verileri DataFrame'i
            
        Returns:
            pd.DataFrame: RSI değerlerini içeren DataFrame
        """
        if data.empty:
            logger.warning("RSI hesaplaması için veri yok")
            return pd.DataFrame()
        
        period = self.params['period']
        column = self.params['column']
        
        if column not in data.columns:
            logger.error(f"{column} sütunu veride bulunamadı")
            return pd.DataFrame()
        
        if len(data) < period:
            logger.warning(f"RSI hesaplaması için yeterli veri yok. En az {period} veri noktası gerekli")
            return pd.DataFrame()
        
        try:
            # Fiyat değişimlerini hesapla
            delta = data[column].diff()
            
            # Pozitif ve negatif değişimleri ayır
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # İlk EMA değerleri için basit ortalama
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # Sonraki değerler için EMA kullan
            for i in range(period, len(delta)):
                avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + gain.iloc[i]) / period
                avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + loss.iloc[i]) / period
            
            # RS hesapla (Relative Strength)
            rs = avg_gain / avg_loss
            
            # RSI hesapla
            rsi = 100 - (100 / (1 + rs))
            
            # NaN değerleri doldur
            rsi = rsi.fillna(50)  # İlk değerler için varsayılan 50
            
            result = pd.DataFrame({
                'rsi': rsi
            }, index=data.index)
            
            logger.debug(f"RSI başarıyla hesaplandı. Son değer: {result['rsi'].iloc[-1]:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"RSI hesaplanırken hata oluştu: {e}")
            return pd.DataFrame()
            
    def is_valid_signal(self, data: pd.DataFrame) -> bool:
        """
        RSI değerine göre geçerli bir sinyal olup olmadığını kontrol eder.
        
        Args:
            data: Kontrol edilecek veri
            
        Returns:
            bool: Sinyal geçerliyse True, değilse False
        """
        if self.result is None or self.result.empty:
            return False
        
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        last_rsi = self.result['rsi'].iloc[-1]
        
        # Aşırı alım veya aşırı satım durumları
        return last_rsi >= overbought or last_rsi <= oversold
    
    def get_signal(self) -> Dict[str, Any]:
        """
        RSI değerine göre alım/satım sinyali üretir.
        
        Returns:
            Dict: Sinyal bilgisi
        """
        if self.result is None or self.result.empty:
            return {'signal': 'NEUTRAL', 'strength': 0, 'value': None}
        
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        last_rsi = self.result['rsi'].iloc[-1]
        
        # Sinyal tipi
        if last_rsi >= overbought:
            signal = 'SELL'
            strength = min(100, (last_rsi - overbought) * 3)  # Aşırı alım gücü
        elif last_rsi <= oversold:
            signal = 'BUY'
            strength = min(100, (oversold - last_rsi) * 3)  # Aşırı satım gücü
        else:
            signal = 'NEUTRAL'
            # Nötr bölge içinde sinyal gücünü hesapla
            mid_point = (overbought + oversold) / 2
            if last_rsi > mid_point:
                strength = (last_rsi - mid_point) / (overbought - mid_point) * 50  # Alımdan uzak
            else:
                strength = (mid_point - last_rsi) / (mid_point - oversold) * 50  # Satımdan uzak
        
        return {
            'signal': signal,
            'strength': float(strength),
            'value': float(last_rsi)
        } 
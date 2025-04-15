"""
RSI Middle Band göstergesi.

PineScript'ten dönüştürülmüş, RSI değerlerinin belirli seviyeleri geçişi ve 
EMA değişimiyle momentum sinyalleri üreten gösterge.
"""
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import numpy as np
import talib
from loguru import logger

from src.indicators.base_indicator import BaseIndicator


class RSIMiddleBand(BaseIndicator):
    """
    RSI Middle Band göstergesi hesaplama sınıfı.
    
    RSI değerlerinin belirli seviyeleri geçişini ve EMA değişimini takip ederek
    alım/satım sinyalleri üretir.
    """
    
    def __init__(
        self, 
        rsi_period: int = 14,
        positive_momentum: int = 50,
        negative_momentum: int = 45,
        ema_short_period: int = 5,
        ema_long_period: int = 10,
        column: str = 'close'
    ):
        """
        RSI Middle Band göstergesini başlatır.
        
        Args:
            rsi_period: RSI hesaplama periyodu (varsayılan: 14)
            positive_momentum: Pozitif momentum için RSI geçiş seviyesi (varsayılan: 50)
            negative_momentum: Negatif momentum için RSI geçiş seviyesi (varsayılan: 45)
            ema_short_period: Kısa EMA periyodu (varsayılan: 5)
            ema_long_period: Uzun EMA periyodu (varsayılan: 10)
            column: Hesaplama için kullanılacak veri sütunu (varsayılan: 'close')
        """
        params = {
            'rsi_period': rsi_period,
            'positive_momentum': positive_momentum,
            'negative_momentum': negative_momentum,
            'ema_short_period': ema_short_period,
            'ema_long_period': ema_long_period,
            'column': column
        }
        super().__init__(name='RSI Middle Band', params=params)
        self.buy_signal = False
        self.sell_signal = False
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        RSI Middle Band değerlerini hesaplar.
        
        Args:
            data: İşlem verileri DataFrame'i
            
        Returns:
            pd.DataFrame: RSI değerlerini içeren DataFrame
        """
        if data.empty:
            logger.warning("RSI Middle Band hesaplaması için veri yok")
            return pd.DataFrame()
        
        rsi_period = self.params['rsi_period']
        positive_momentum = self.params['positive_momentum']
        negative_momentum = self.params['negative_momentum']
        ema_short_period = self.params['ema_short_period']
        ema_long_period = self.params['ema_long_period']
        column = self.params['column']
        
        if column not in data.columns:
            logger.error(f"{column} sütunu veride bulunamadı")
            return pd.DataFrame()
        
        if len(data) < max(rsi_period, ema_short_period, ema_long_period) + 1:
            logger.warning(f"RSI Middle Band hesaplaması için yeterli veri yok.")
            return pd.DataFrame()
        
        try:
            # RSI ve EMA hesapla
            rsi = pd.Series(talib.RSI(data[column].values, timeperiod=rsi_period), index=data.index)
            ema_short = pd.Series(talib.EMA(data[column].values, timeperiod=ema_short_period), index=data.index)
            ema_high = pd.Series(talib.EMA(data['high'].values, timeperiod=ema_short_period), index=data.index)
            ema_low = pd.Series(talib.EMA(data['low'].values, timeperiod=ema_long_period), index=data.index)
            
            # Momentum koşulları
            p_mom = pd.Series(False, index=data.index)
            n_mom = pd.Series(False, index=data.index)
            
            # Buy ve Sell sinyalleri
            buy_signals = pd.Series(False, index=data.index)
            sell_signals = pd.Series(False, index=data.index)
            
            # İlk değerler için sinyali önceki değere ayarla
            buy_signals.iloc[0] = self.buy_signal
            sell_signals.iloc[0] = self.sell_signal
            
            for i in range(1, len(data)):
                # EMA değişimini hesapla
                ema_change = ema_short.iloc[i] - ema_short.iloc[i-1]
                
                # Pozitif momentum: RSI, prev_value < positive_level, current_value > positive_level ve RSI > negative_level
                # ve EMA'nın pozitif yönde değişmesi durumu
                p_mom.iloc[i] = (rsi.iloc[i-1] < positive_momentum and 
                                 rsi.iloc[i] > positive_momentum and 
                                 rsi.iloc[i] > negative_momentum and 
                                 ema_change > 0)
                
                # Negatif momentum: RSI < negative_level ve EMA'nın negatif yönde değişmesi durumu
                n_mom.iloc[i] = (rsi.iloc[i] < negative_momentum and ema_change < 0)
                
                # Alım/Satım sinyalleri güncelle
                if p_mom.iloc[i]:
                    buy_signals.iloc[i] = True
                    sell_signals.iloc[i] = False
                elif n_mom.iloc[i]:
                    buy_signals.iloc[i] = False
                    sell_signals.iloc[i] = True
                else:
                    # Önceki durum devam eder
                    buy_signals.iloc[i] = buy_signals.iloc[i-1]
                    sell_signals.iloc[i] = sell_signals.iloc[i-1]
            
            # Son durum güncelle
            self.buy_signal = buy_signals.iloc[-1]
            self.sell_signal = sell_signals.iloc[-1]
            
            # Sonuçları DataFrame'e dönüştür
            result = pd.DataFrame({
                'rsi': rsi,
                'ema_short': ema_short,
                'ema_high': ema_high,
                'ema_low': ema_low,
                'positive_momentum': p_mom,
                'negative_momentum': n_mom,
                'buy_signal': buy_signals,
                'sell_signal': sell_signals
            }, index=data.index)
            
            logger.debug(f"RSI Middle Band başarıyla hesaplandı. Son RSI: {result['rsi'].iloc[-1]:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"RSI Middle Band hesaplanırken hata oluştu: {e}")
            return pd.DataFrame()
    
    def is_buy_signal(self) -> bool:
        """
        Alım sinyali olup olmadığını kontrol eder.
        
        Returns:
            bool: Alım sinyali varsa True, yoksa False
        """
        if self.result is None or self.result.empty:
            return False
        
        return self.result['buy_signal'].iloc[-1]
    
    def is_sell_signal(self) -> bool:
        """
        Satım sinyali olup olmadığını kontrol eder.
        
        Returns:
            bool: Satım sinyali varsa True, yoksa False
        """
        if self.result is None or self.result.empty:
            return False
        
        return self.result['sell_signal'].iloc[-1]
    
    def is_valid_signal(self, data: pd.DataFrame) -> bool:
        """
        Geçerli bir sinyal olup olmadığını kontrol eder.
        
        Args:
            data: Kontrol edilecek veri
            
        Returns:
            bool: Sinyal geçerliyse True, değilse False
        """
        return self.is_buy_signal() or self.is_sell_signal()
    
    def get_signal(self) -> Dict[str, Any]:
        """
        RSI Middle Band göstergesine göre alım/satım sinyali üretir.
        
        Returns:
            Dict: Sinyal bilgisi
        """
        if self.result is None or self.result.empty:
            return {'signal': 'NEUTRAL', 'strength': 0, 'value': None}
        
        last_rsi = self.result['rsi'].iloc[-1]
        positive_momentum = self.params['positive_momentum']
        negative_momentum = self.params['negative_momentum']
        
        if self.is_buy_signal():
            signal = 'BUY'
            # Sinyalin gücünü hesapla
            if last_rsi > positive_momentum:
                strength = min(100, (last_rsi - positive_momentum) * 2)
            else:
                strength = 50  # Varsayılan güç
        elif self.is_sell_signal():
            signal = 'SELL'
            # Sinyalin gücünü hesapla
            if last_rsi < negative_momentum:
                strength = min(100, (negative_momentum - last_rsi) * 2)
            else:
                strength = 50  # Varsayılan güç
        else:
            signal = 'NEUTRAL'
            strength = 0
        
        return {
            'signal': signal,
            'strength': float(strength),
            'value': float(last_rsi),
            'buy_signal': bool(self.is_buy_signal()),
            'sell_signal': bool(self.is_sell_signal())
        }
    
    def plot_data(self, ax, data: pd.DataFrame) -> None:
        """
        Gösterge verilerini grafik üzerine çizer.
        
        Args:
            ax: Matplotlib ekseni
            data: Çizilecek veri
        """
        if self.result is None or self.result.empty:
            logger.warning("Grafik çizimi için veri bulunamadı")
            return
        
        try:
            # RSI çizgisini çiz
            ax.plot(self.result.index, self.result['rsi'], label='RSI', color='blue')
            
            # Pozitif ve negatif momentum seviyelerini çiz
            ax.axhline(y=self.params['positive_momentum'], color='green', linestyle='--', alpha=0.7, 
                       label=f"Positive Momentum ({self.params['positive_momentum']})")
            ax.axhline(y=self.params['negative_momentum'], color='red', linestyle='--', alpha=0.7,
                       label=f"Negative Momentum ({self.params['negative_momentum']})")
            
            # Alım sinyallerini işaretle
            buy_points = self.result[self.result['buy_signal'] & ~self.result['buy_signal'].shift(1).fillna(False)]
            if not buy_points.empty:
                ax.scatter(buy_points.index, buy_points['rsi'], color='green', marker='^', s=100, label='Buy Signal')
            
            # Satım sinyallerini işaretle
            sell_points = self.result[self.result['sell_signal'] & ~self.result['sell_signal'].shift(1).fillna(False)]
            if not sell_points.empty:
                ax.scatter(sell_points.index, sell_points['rsi'], color='red', marker='v', s=100, label='Sell Signal')
            
            # Grafik özellikleri
            ax.set_title('RSI Middle Band')
            ax.set_ylabel('RSI Value')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
        except Exception as e:
            logger.error(f"Grafik çizilirken hata oluştu: {e}") 
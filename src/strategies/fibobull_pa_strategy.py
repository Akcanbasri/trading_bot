"""
Fibobull PA stratejisi.

Bu strateji, Fibobull PA göstergesine dayalı olarak alış/satış sinyalleri üretir.
Destek ve direnç seviyelerini hesaplar ve trend değişimlerine göre sinyaller üretir.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from src.data.market_data import MarketDataCollector
from src.strategies.base_strategy import BaseStrategy
from src.utils.exceptions import InsufficientDataError, CalculationError, StrategyError

logger = logging.getLogger(__name__)

class FibobullPAStrategy(BaseStrategy):
    """
    Fibobull PA stratejisi.
    
    Bu strateji, pivot noktalarını kullanarak destek ve direnç seviyelerini hesaplar
    ve trend değişimlerine göre alış/satış sinyalleri üretir.
    
    Attributes:
        left_bars (int): Sol taraftaki bar sayısı (pivot noktalarını bulmak için)
        right_bars (int): Sağ taraftaki bar sayısı (pivot noktalarını bulmak için)
        market_data (MarketDataCollector): Market veri toplayıcı
    """
    
    def __init__(
        self,
        market_data: MarketDataCollector,
        left_bars: int = 8,
        right_bars: int = 8
    ):
        """
        Fibobull PA stratejisini başlatır.
        
        Args:
            market_data (MarketDataCollector): Market veri toplayıcı
            left_bars (int, optional): Sol taraftaki bar sayısı. Varsayılan 8.
            right_bars (int, optional): Sağ taraftaki bar sayısı. Varsayılan 8.
        """
        if left_bars <= 0 or right_bars <= 0:
            raise ValueError("Bar sayıları pozitif olmalıdır")
        
        name = f"Fibobull_PA_{left_bars}_{right_bars}"
        super().__init__(name=name, market_data=market_data)
        
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.description = f"Fibobull PA stratejisi ({left_bars}/{right_bars} barlar)"
        self.required_data_length = left_bars + right_bars + 10  # Hesaplamalar için ek tampon
        self.last_signal = None
        
        # Strateji durumu
        self.trend = 0  # 1: yukarı trend, -1: aşağı trend, 0: belirsiz
        self.resistance = None  # Direnç seviyesi
        self.support = None  # Destek seviyesi
        
        logger.info(f"Fibobull PA stratejisi başlatıldı: {self.name}")
    
    def find_pivot_points(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Pivot noktalarını bulur.
        
        Args:
            df (pd.DataFrame): Fiyat verileri içeren DataFrame
            
        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: Pivot yüksek, pivot düşük ve trend yönü
        """
        high = df['high']
        low = df['low']
        
        # Pivot yüksek noktaları
        pivot_high = pd.Series(index=df.index, dtype=float)
        for i in range(self.left_bars, len(df) - self.right_bars):
            if all(high.iloc[i] > high.iloc[i-self.left_bars:i]) and all(high.iloc[i] > high.iloc[i+1:i+self.right_bars+1]):
                pivot_high.iloc[i] = high.iloc[i]
        
        # Pivot düşük noktaları
        pivot_low = pd.Series(index=df.index, dtype=float)
        for i in range(self.left_bars, len(df) - self.right_bars):
            if all(low.iloc[i] < low.iloc[i-self.left_bars:i]) and all(low.iloc[i] < low.iloc[i+1:i+self.right_bars+1]):
                pivot_low.iloc[i] = low.iloc[i]
        
        # Trend yönü
        trend = pd.Series(index=df.index, dtype=int)
        trend[pivot_high.notna()] = 1  # Yüksek pivot: yukarı trend
        trend[pivot_low.notna()] = -1  # Düşük pivot: aşağı trend
        
        # Trend değerlerini doldur
        trend = trend.fillna(method='ffill')
        
        return pivot_high, pivot_low, trend
    
    def find_patterns(self, df: pd.DataFrame, pivot_high: pd.Series, pivot_low: pd.Series) -> Dict[str, pd.Series]:
        """
        HH, LL, HL, LH formasyonlarını bulur.
        
        Args:
            df (pd.DataFrame): Fiyat verileri içeren DataFrame
            pivot_high (pd.Series): Pivot yüksek noktaları
            pivot_low (pd.Series): Pivot düşük noktaları
            
        Returns:
            Dict[str, pd.Series]: Formasyonlar
        """
        high = df['high']
        low = df['low']
        
        # Formasyonlar
        hh = pd.Series(False, index=df.index)  # Higher High
        ll = pd.Series(False, index=df.index)  # Lower Low
        hl = pd.Series(False, index=df.index)  # Higher Low
        lh = pd.Series(False, index=df.index)  # Lower High
        
        # Son 5 pivot noktasını bul
        for i in range(5, len(df)):
            pivots = []
            
            # Son 5 pivot noktasını bul
            for j in range(i, max(0, i-20), -1):
                if not pd.isna(pivot_high.iloc[j]):
                    pivots.append((j, pivot_high.iloc[j], 'high'))
                if not pd.isna(pivot_low.iloc[j]):
                    pivots.append((j, pivot_low.iloc[j], 'low'))
            
            if len(pivots) >= 5:
                pivots = pivots[:5]  # Son 5 pivot noktasını al
                
                # Formasyonları kontrol et
                if pivots[0][2] == 'high' and pivots[1][2] == 'high' and pivots[2][2] == 'low' and pivots[3][2] == 'high' and pivots[4][2] == 'low':
                    # HH formasyonu
                    if pivots[0][1] > pivots[1][1] and pivots[1][1] > pivots[2][1] and pivots[2][1] > pivots[3][1] and pivots[3][1] > pivots[4][1]:
                        hh.iloc[i] = True
                
                elif pivots[0][2] == 'low' and pivots[1][2] == 'low' and pivots[2][2] == 'high' and pivots[3][2] == 'low' and pivots[4][2] == 'high':
                    # LL formasyonu
                    if pivots[0][1] < pivots[1][1] and pivots[1][1] < pivots[2][1] and pivots[2][1] < pivots[3][1] and pivots[3][1] < pivots[4][1]:
                        ll.iloc[i] = True
                
                elif pivots[0][2] == 'low' and pivots[1][2] == 'high' and pivots[2][2] == 'low' and pivots[3][2] == 'high' and pivots[4][2] == 'low':
                    # HL formasyonu
                    if pivots[0][1] > pivots[2][1] and pivots[2][1] > pivots[4][1]:
                        hl.iloc[i] = True
                
                elif pivots[0][2] == 'high' and pivots[1][2] == 'low' and pivots[2][2] == 'high' and pivots[3][2] == 'low' and pivots[4][2] == 'high':
                    # LH formasyonu
                    if pivots[0][1] < pivots[2][1] and pivots[2][1] < pivots[4][1]:
                        lh.iloc[i] = True
        
        return {
            'hh': hh,
            'll': ll,
            'hl': hl,
            'lh': lh
        }
    
    def calculate_support_resistance(self, df: pd.DataFrame, patterns: Dict[str, pd.Series], pivot_high: pd.Series, pivot_low: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Destek ve direnç seviyelerini hesaplar.
        
        Args:
            df (pd.DataFrame): Fiyat verileri içeren DataFrame
            patterns (Dict[str, pd.Series]): Formasyonlar
            pivot_high (pd.Series): Pivot yüksek noktaları
            pivot_low (pd.Series): Pivot düşük noktaları
            
        Returns:
            Tuple[pd.Series, pd.Series]: Direnç ve destek seviyeleri
        """
        close = df['close']
        
        # Direnç ve destek seviyeleri
        resistance = pd.Series(index=df.index, dtype=float)
        support = pd.Series(index=df.index, dtype=float)
        
        # Trend yönünü belirle
        trend = pd.Series(0, index=df.index)
        for i in range(1, len(df)):
            if close.iloc[i] > resistance.iloc[i-1] if not pd.isna(resistance.iloc[i-1]) else False:
                trend.iloc[i] = 1
            elif close.iloc[i] < support.iloc[i-1] if not pd.isna(support.iloc[i-1]) else False:
                trend.iloc[i] = -1
            else:
                trend.iloc[i] = trend.iloc[i-1]
        
        # Direnç ve destek seviyelerini güncelle
        for i in range(1, len(df)):
            # Direnç seviyesi
            if patterns['lh'].iloc[i] and not pd.isna(pivot_high.iloc[i]):
                resistance.iloc[i] = pivot_high.iloc[i]
            elif (trend.iloc[i] == 1 and patterns['hh'].iloc[i]) or (trend.iloc[i] == -1 and patterns['lh'].iloc[i]):
                if not pd.isna(pivot_high.iloc[i]):
                    resistance.iloc[i] = pivot_high.iloc[i]
                else:
                    resistance.iloc[i] = resistance.iloc[i-1]
            else:
                resistance.iloc[i] = resistance.iloc[i-1]
            
            # Destek seviyesi
            if patterns['hl'].iloc[i] and not pd.isna(pivot_low.iloc[i]):
                support.iloc[i] = pivot_low.iloc[i]
            elif (trend.iloc[i] == 1 and patterns['hl'].iloc[i]) or (trend.iloc[i] == -1 and patterns['ll'].iloc[i]):
                if not pd.isna(pivot_low.iloc[i]):
                    support.iloc[i] = pivot_low.iloc[i]
                else:
                    support.iloc[i] = support.iloc[i-1]
            else:
                support.iloc[i] = support.iloc[i-1]
        
        return resistance, support
    
    def generate_signals(self, df: pd.DataFrame, resistance: pd.Series, support: pd.Series, trend: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Alış ve satış sinyallerini üretir.
        
        Args:
            df (pd.DataFrame): Fiyat verileri içeren DataFrame
            resistance (pd.Series): Direnç seviyeleri
            support (pd.Series): Destek seviyeleri
            trend (pd.Series): Trend yönü
            
        Returns:
            Tuple[pd.Series, pd.Series]: Alış ve satış sinyalleri
        """
        # Alış ve satış sinyalleri
        long_signal = pd.Series(False, index=df.index)
        short_signal = pd.Series(False, index=df.index)
        
        # Trend değişimlerine göre sinyaller üret
        for i in range(1, len(df)):
            # Alış sinyali: Trend yukarı yöne döndüğünde
            if trend.iloc[i-1] != 1 and trend.iloc[i] == 1:
                long_signal.iloc[i] = True
            
            # Satış sinyali: Trend aşağı yöne döndüğünde
            if trend.iloc[i-1] != -1 and trend.iloc[i] == -1:
                short_signal.iloc[i] = True
        
        return long_signal, short_signal
    
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
            
            if df.empty or len(df) < self.required_data_length:
                raise InsufficientDataError(
                    f"{symbol} için yeterli veri yok. "
                    f"En az {self.required_data_length} bar gerekli."
                )
            
            # Pivot noktalarını bul
            pivot_high, pivot_low, trend = self.find_pivot_points(df)
            
            # Formasyonları bul
            patterns = self.find_patterns(df, pivot_high, pivot_low)
            
            # Destek ve direnç seviyelerini hesapla
            resistance, support = self.calculate_support_resistance(df, patterns, pivot_high, pivot_low)
            
            # Güncel fiyat
            current_price = df["close"].iloc[-1]
            
            # Sinyal üret
            signal = "NEUTRAL"
            strength = 0.0
            
            # Son 5 mum için formasyonları kontrol et
            last_5_hh = patterns["hh"].iloc[-5:].any()
            last_5_ll = patterns["ll"].iloc[-5:].any()
            last_5_hl = patterns["hl"].iloc[-5:].any()
            last_5_lh = patterns["lh"].iloc[-5:].any()
            
            # Trend yönünü belirle
            if last_5_hh and last_5_hl:  # Yükselen trend
                signal = "LONG"
                strength = 0.8
            elif last_5_ll and last_5_lh:  # Düşen trend
                signal = "SHORT"
                strength = 0.8
            
            # Son sinyali güncelle
            self.last_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "strength": strength,
                "current_price": current_price,
                "resistance": resistance.iloc[-1] if not pd.isna(resistance.iloc[-1]) else None,
                "support": support.iloc[-1] if not pd.isna(support.iloc[-1]) else None,
                "trend": trend.iloc[-1]
            }
            
            return self.last_signal
            
        except Exception as e:
            logger.error(f"Sinyal üretilirken hata oluştu: {str(e)}")
            raise 
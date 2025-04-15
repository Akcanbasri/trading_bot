"""
FiboBULL PA göstergesi.

Bu gösterge pivot high/low noktalarını tespit eder, trend yönünü belirler 
ve destek-direnç seviyelerini hesaplar.

Original PineScript göstergesinden Python'a çevrilmiştir.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from src.indicators.base_indicator import BaseIndicator


class FiboBULLPA(BaseIndicator):
    """
    FiboBULL PA göstergesi hesaplama sınıfı.
    
    Pivot high/low noktalarını tespit eder, trend yönünü belirler, 
    ve destek-direnç seviyelerini hesaplar.
    """
    
    def __init__(
        self,
        left_bars: int = 8,
        right_bars: int = 8,
        show_sup_res: bool = True,
    ):
        """
        FiboBULL PA göstergesini başlatır.
        
        Args:
            left_bars: Pivot noktası tespiti için sol bar sayısı (varsayılan: 8)
            right_bars: Pivot noktası tespiti için sağ bar sayısı (varsayılan: 8)
            show_sup_res: Destek-direnç çizgilerini gösterme durumu (varsayılan: True)
        """
        params = {
            'left_bars': left_bars,
            'right_bars': right_bars,
            'show_sup_res': show_sup_res
        }
        super().__init__(name='FiboBULL PA', params=params)
        
        # Sınıf değişkenleri
        self.trend = None
        self.zz = None
        self.support = None
        self.resistance = None
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        FiboBULL PA değerlerini hesaplar.
        
        Args:
            data: İşlem verileri DataFrame'i ('high', 'low', 'close' sütunları gerekli)
            
        Returns:
            pd.DataFrame: Hesaplama sonuçlarını içeren DataFrame
        """
        if data.empty:
            logger.warning("FiboBULL PA hesaplaması için veri yok")
            return pd.DataFrame()
        
        required_columns = ['high', 'low', 'close']
        if not all(col in data.columns for col in required_columns):
            logger.error(f"Veri sütunları eksik. Gerekli sütunlar: {required_columns}")
            return pd.DataFrame()
        
        left_bars = self.params['left_bars']
        right_bars = self.params['right_bars']
        
        # Minimum gereken veri boyutu
        min_data_size = left_bars + right_bars + 10
        if len(data) < min_data_size:
            logger.warning(f"FiboBULL PA hesaplaması için yeterli veri yok. En az {min_data_size} veri noktası gerekli")
            return pd.DataFrame()
        
        try:
            # Verileri kopyala
            df = data.copy()
            
            # Pivot High/Low hesaplaması
            a, b, c, d, e, df = self._find_previous_points(df, left_bars, right_bars)
            
            # Higher High, Lower Low, Higher Low, Lower High hesaplama
            higher_high, lower_low, higher_low, lower_high = self._calculate_hl_patterns(a, b, c, d, e)
            
            # Destek ve direnç hesaplama
            resistance, support = self._calculate_support_resistance(df, higher_high, lower_low, higher_low, lower_high)
            
            # Trend yönünü belirle
            trend = self._calculate_trend(df, resistance, support)
            
            # Long ve short sinyalleri
            long_signal, short_signal = self._calculate_signals(df, trend)
            
            # Sonuçları DataFrame'e ekle
            result = pd.DataFrame({
                'trend': trend,
                'resistance': resistance,
                'support': support,
                'higher_high': higher_high,
                'lower_low': lower_low,
                'higher_low': higher_low,
                'lower_high': lower_high,
                'long_signal': long_signal,
                'short_signal': short_signal
            }, index=df.index)
            
            # Sınıf değişkenlerini güncelle
            self.trend = trend
            self.zz = df['zz'] if 'zz' in df.columns else None
            self.support = support
            self.resistance = resistance
            
            logger.debug(f"FiboBULL PA başarıyla hesaplandı. Son trend: {trend.iloc[-1] if not trend.empty else 'NA'}")
            return result
            
        except Exception as e:
            logger.error(f"FiboBULL PA hesaplanırken hata oluştu: {e}")
            return pd.DataFrame()
    
    def _find_previous_points(self, df: pd.DataFrame, lb: int, rb: int) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.DataFrame]:
        """
        Önceki pivot noktalarını bulur.
        
        Args:
            df: İşlem verileri DataFrame'i
            lb: Sol bar sayısı
            rb: Sağ bar sayısı
            
        Returns:
            Tuple: a, b, c, d, e pivot serileri ve pivot bilgisiyle güncellenen dataframe
        """
        # Pivot high/low hesaplama
        ph = df['high'].rolling(window=lb+rb+1, center=True).apply(lambda x: x[lb] == max(x), raw=True)
        pl = df['low'].rolling(window=lb+rb+1, center=True).apply(lambda x: x[lb] == min(x), raw=True)
        
        # Trend yönü (1: yukarı, -1: aşağı)
        hl = pd.Series(np.nan, index=df.index)
        hl.loc[ph] = 1
        hl.loc[pl] = -1
        df['hl'] = hl
        
        # Zigzag hesaplama (pivot değerleri)
        zz = pd.Series(np.nan, index=df.index)
        zz.loc[ph] = df.loc[ph, 'high']
        zz.loc[pl] = df.loc[pl, 'low']
        df['zz'] = zz
        
        # Sıralı pivot noktalarını bulma
        a, b, c, d, e = pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index)
        
        # PineScript'teki findprevious() fonksiyonunun mantığını uygula
        for i in range(len(df)-rb-1, rb, -1):
            if pd.notna(df.loc[df.index[i], 'zz']):
                if pd.isna(a.iloc[i]):
                    a.iloc[i] = df.loc[df.index[i], 'zz']
                    continue
                
                if pd.isna(b.iloc[i]) and pd.notna(a.iloc[i]):
                    if df.loc[df.index[i], 'hl'] != df.loc[df.index[i-1], 'hl']:
                        b.iloc[i] = df.loc[df.index[i], 'zz']
                        continue
                
                if pd.isna(c.iloc[i]) and pd.notna(b.iloc[i]):
                    if df.loc[df.index[i], 'hl'] == df.loc[df.index[i-1], 'hl']:
                        c.iloc[i] = df.loc[df.index[i], 'zz']
                        continue
                
                if pd.isna(d.iloc[i]) and pd.notna(c.iloc[i]):
                    if df.loc[df.index[i], 'hl'] != df.loc[df.index[i-1], 'hl']:
                        d.iloc[i] = df.loc[df.index[i], 'zz']
                        continue
                
                if pd.isna(e.iloc[i]) and pd.notna(d.iloc[i]):
                    if df.loc[df.index[i], 'hl'] == df.loc[df.index[i-1], 'hl']:
                        e.iloc[i] = df.loc[df.index[i], 'zz']
        
        return a, b, c, d, e, df
    
    def _calculate_hl_patterns(self, a: pd.Series, b: pd.Series, c: pd.Series, d: pd.Series, e: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Higher High, Lower Low, Higher Low, Lower High paternlerini hesaplar.
        
        Args:
            a: Birinci pivot noktası serisi
            b: İkinci pivot noktası serisi
            c: Üçüncü pivot noktası serisi
            d: Dördüncü pivot noktası serisi
            e: Beşinci pivot noktası serisi
            
        Returns:
            Tuple: higher_high, lower_low, higher_low, lower_high paternleri (boolean seriler)
        """
        # Higher High (HH)
        higher_high = (pd.notna(a) & pd.notna(b) & pd.notna(c) & 
                       (a > b) & (a > c) & (c > b) & (c > d))
        
        # Lower Low (LL)
        lower_low = (pd.notna(a) & pd.notna(b) & pd.notna(c) & 
                     (a < b) & (a < c) & (c < b) & (c < d))
        
        # Higher Low (HL)
        higher_low = ((pd.notna(a) & pd.notna(c) & (a >= c) & 
                      (pd.notna(b) & pd.notna(d) & (b > c) & (b > d) & (d > c) & (d > e))) | 
                      (pd.notna(a) & pd.notna(b) & pd.notna(c) & 
                      (a < b) & (a > c) & (b < d)))
        
        # Lower High (LH)
        lower_high = ((pd.notna(a) & pd.notna(c) & (a <= c) & 
                      (pd.notna(b) & pd.notna(d) & (b < c) & (b < d) & (d < c) & (d < e))) | 
                      (pd.notna(a) & pd.notna(b) & pd.notna(c) & 
                      (a > b) & (a < c) & (b > d)))
        
        return higher_high, lower_low, higher_low, lower_high
    
    def _calculate_support_resistance(self, df: pd.DataFrame, higher_high: pd.Series, lower_low: pd.Series, higher_low: pd.Series, lower_high: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Destek ve direnç seviyelerini hesaplar.
        
        Args:
            df: İşlem verileri DataFrame'i (zz sütunu içermeli)
            higher_high: Higher High paterni serisi
            lower_low: Lower Low paterni serisi
            higher_low: Higher Low paterni serisi
            lower_high: Lower High paterni serisi
            
        Returns:
            Tuple: resistance, support serileri
        """
        # Boş destek ve direnç serileri oluştur
        resistance = pd.Series(np.nan, index=df.index)
        support = pd.Series(np.nan, index=df.index)
        
        # İlk değerleri hesapla
        for i in range(len(df)):
            if lower_high.iloc[i]:
                resistance.iloc[i] = df['zz'].iloc[i]
            elif higher_low.iloc[i]:
                support.iloc[i] = df['zz'].iloc[i]
        
        # Değerleri ileri doğru doldur
        resistance = resistance.fillna(method='ffill')
        support = support.fillna(method='ffill')
        
        return resistance, support
    
    def _calculate_trend(self, df: pd.DataFrame, resistance: pd.Series, support: pd.Series) -> pd.Series:
        """
        Trend yönünü hesaplar.
        
        Args:
            df: İşlem verileri DataFrame'i
            resistance: Direnç seviyeleri serisi
            support: Destek seviyeleri serisi
            
        Returns:
            pd.Series: trend serisi (1: yukarı trend, -1: aşağı trend)
        """
        # Boş trend serisi oluştur
        trend = pd.Series(np.nan, index=df.index)
        
        # Trend yönünü belirle
        for i in range(1, len(df)):
            if pd.isna(trend.iloc[i-1]):
                # İlk trend belirlemesi
                if df['close'].iloc[i] > resistance.iloc[i]:
                    trend.iloc[i] = 1  # Yukarı trend
                elif df['close'].iloc[i] < support.iloc[i]:
                    trend.iloc[i] = -1  # Aşağı trend
                else:
                    trend.iloc[i] = 0  # Belirsiz/yatay trend
            else:
                # Mevcut trendi koru veya değiştir
                if df['close'].iloc[i] > resistance.iloc[i]:
                    trend.iloc[i] = 1
                elif df['close'].iloc[i] < support.iloc[i]:
                    trend.iloc[i] = -1
                else:
                    trend.iloc[i] = trend.iloc[i-1]
        
        # İlk değeri doldur
        trend.iloc[0] = trend.iloc[1] if pd.notna(trend.iloc[1]) else 0
        
        return trend
    
    def _calculate_signals(self, df: pd.DataFrame, trend: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Alım/satım sinyallerini hesaplar.
        
        Args:
            df: İşlem verileri DataFrame'i
            trend: Trend yönü serisi
            
        Returns:
            Tuple: long_signal, short_signal serileri (boolean)
        """
        # Boş sinyal serileri oluştur
        long_signal = pd.Series(False, index=df.index)
        short_signal = pd.Series(False, index=df.index)
        
        # Sinyalleri hesapla (PineScript'teki long_signal ve short_signal)
        for i in range(1, len(df)):
            # Long sinyali
            long_signal.iloc[i] = (trend.iloc[i-1] != 1) and (trend.iloc[i] == 1)
            
            # Short sinyali
            short_signal.iloc[i] = (trend.iloc[i-1] != -1) and (trend.iloc[i] == -1)
        
        return long_signal, short_signal
    
    def get_current_trend(self) -> Optional[int]:
        """
        Mevcut trend yönünü döndürür.
        
        Returns:
            Optional[int]: 1 (yukarı trend), -1 (aşağı trend), 0 (yatay), None (hesaplanmamış)
        """
        if self.result is None or self.result.empty:
            return None
        
        if 'trend' not in self.result.columns:
            return None
        
        return int(self.result['trend'].iloc[-1])
    
    def get_support_resistance(self) -> Dict[str, float]:
        """
        Mevcut destek ve direnç seviyelerini döndürür.
        
        Returns:
            Dict[str, float]: {'support': destek_seviyesi, 'resistance': direnç_seviyesi}
        """
        if self.result is None or self.result.empty:
            return {'support': None, 'resistance': None}
        
        support = None
        resistance = None
        
        if 'support' in self.result.columns:
            support = self.result['support'].iloc[-1]
            
        if 'resistance' in self.result.columns:
            resistance = self.result['resistance'].iloc[-1]
            
        return {'support': support, 'resistance': resistance}
    
    def is_valid_signal(self, data: pd.DataFrame = None) -> bool:
        """
        Geçerli bir sinyal olup olmadığını kontrol eder.
        
        Args:
            data: Ek veri (kullanılmıyor, BaseIndicator sınıfından override edilmiş)
            
        Returns:
            bool: Sinyal varsa True, yoksa False
        """
        if self.result is None or self.result.empty:
            return False
        
        # Son sinyalleri kontrol et
        long_signal = self.result['long_signal'].iloc[-1]
        short_signal = self.result['short_signal'].iloc[-1]
        
        return long_signal or short_signal
    
    def get_signal(self) -> Dict[str, Any]:
        """
        Mevcut sinyal bilgisini döndürür.
        
        Returns:
            Dict[str, Any]: Sinyal bilgisi
        """
        if self.result is None or self.result.empty:
            return {'signal': 'NEUTRAL', 'side': None, 'strength': 0}
        
        # Son sinyalleri kontrol et
        long_signal = self.result['long_signal'].iloc[-1]
        short_signal = self.result['short_signal'].iloc[-1]
        
        # Trend yönü
        trend = self.get_current_trend()
        
        if long_signal:
            return {
                'signal': 'BUY',
                'side': 'LONG',
                'strength': 100,  # Tam güçte sinyal
                'trend': trend
            }
        elif short_signal:
            return {
                'signal': 'SELL',
                'side': 'SHORT',
                'strength': 100,  # Tam güçte sinyal
                'trend': trend
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'side': None,
                'strength': 0,
                'trend': trend
            } 
"""
FiboBULL PA göstergesine dayalı trading stratejisi.

Bu modül, FiboBULL PA göstergesini kullanarak alım/satım sinyalleri üretir.
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np
from loguru import logger

from src.indicators.fibobuLL_pa import FiboBULLPA


class FiboBULLStrategy:
    """
    FiboBULL PA göstergesine dayalı trading stratejisi.
    
    Bu strateji, FiboBULL PA göstergesinin trend, destek-direnç ve 
    sinyal hesaplamalarını kullanarak alım/satım kararları verir.
    """
    
    def __init__(
        self,
        left_bars: int = 8,
        right_bars: int = 8,
        use_confirmations: bool = True,
        stop_loss_percent: float = 3.0,
        take_profit_percent: float = 6.0
    ):
        """
        FiboBULL stratejisini başlatır.
        
        Args:
            left_bars: Pivot noktası tespiti için sol bar sayısı (varsayılan: 8)
            right_bars: Pivot noktası tespiti için sağ bar sayısı (varsayılan: 8)
            use_confirmations: Ek onay göstergeleri kullanılsın mı (varsayılan: True)
            stop_loss_percent: Stop-loss yüzdesi (varsayılan: 3.0)
            take_profit_percent: Take-profit yüzdesi (varsayılan: 6.0)
        """
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.use_confirmations = use_confirmations
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        
        # FiboBULL PA göstergesini oluştur
        self.indicator = FiboBULLPA(
            left_bars=left_bars,
            right_bars=right_bars,
            show_sup_res=True
        )
        
        # Strateji durumu
        self.current_position = None  # 'long', 'short', None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        
        # Sonuçları saklamak için
        self.signals: List[Dict[str, Any]] = []
        
        logger.info(f"FiboBULL stratejisi başlatıldı. LB={left_bars}, RB={right_bars}")
    
    def update(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Stratejiyi yeni veriyle günceller ve sinyal üretir.
        
        Args:
            data: OHLCV verileri (high, low, close sütunları gerekli)
            
        Returns:
            Dict[str, Any]: Strateji sonucu ve sinyal bilgisi
        """
        if data.empty:
            return {'signal': 'NEUTRAL', 'reason': 'Veri yok'}
        
        # Göstergeyi hesapla
        self.indicator.calculate(data)
        
        # Gösterge sinyalini al
        indicator_signal = self.indicator.get_signal()
        
        # Strateji sinyalini oluştur
        strategy_signal = self._generate_strategy_signal(data, indicator_signal)
        
        # Sonucu kaydet
        self.signals.append(strategy_signal)
        
        return strategy_signal
    
    def _generate_strategy_signal(self, data: pd.DataFrame, indicator_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gösterge sinyaline ve mevcut duruma göre strateji sinyali üretir.
        
        Args:
            data: Güncel OHLCV verisi
            indicator_signal: Göstergeden gelen sinyal
            
        Returns:
            Dict[str, Any]: Strateji sinyali
        """
        if data.empty:
            return {'signal': 'NEUTRAL', 'reason': 'Veri yok'}
        
        # Güncel fiyat
        current_price = data['close'].iloc[-1]
        
        # Strateji sonucu
        result = {
            'signal': 'NEUTRAL',  # NEUTRAL, BUY, SELL
            'side': None,         # None, LONG, SHORT
            'action': 'HOLD',     # HOLD, ENTER, EXIT
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'reason': '',
            'indicator_values': self.indicator.get_support_resistance(),
            'trend': self.indicator.get_current_trend()
        }
        
        # Mevcut pozisyon yoksa yeni pozisyon değerlendir
        if self.current_position is None:
            if indicator_signal['signal'] == 'BUY':
                # Alım (long) sinyali
                self.current_position = 'long'
                self.entry_price = current_price
                self.stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                self.take_profit = current_price * (1 + self.take_profit_percent / 100)
                
                result.update({
                    'signal': 'BUY',
                    'side': 'LONG',
                    'action': 'ENTER',
                    'entry_price': self.entry_price,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'reason': 'Trend değişimi: Yukarı trend'
                })
                
            elif indicator_signal['signal'] == 'SELL':
                # Satım (short) sinyali
                self.current_position = 'short'
                self.entry_price = current_price
                self.stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                self.take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                result.update({
                    'signal': 'SELL',
                    'side': 'SHORT',
                    'action': 'ENTER',
                    'entry_price': self.entry_price,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'reason': 'Trend değişimi: Aşağı trend'
                })
        
        # Mevcut pozisyon varsa çıkış koşullarını kontrol et
        else:
            if self.current_position == 'long':
                if indicator_signal['signal'] == 'SELL':
                    # Trendde değişim, long pozisyonu kapat
                    result.update({
                        'signal': 'SELL',
                        'side': 'LONG',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (current_price - self.entry_price) / self.entry_price * 100,
                        'reason': 'Trend değişimi: Aşağı trendin başlangıcı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
                    
                elif current_price <= self.stop_loss:
                    # Stop-loss seviyesine ulaşıldı, pozisyonu kapat
                    result.update({
                        'signal': 'SELL',
                        'side': 'LONG',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (current_price - self.entry_price) / self.entry_price * 100,
                        'reason': 'Stop-loss seviyesine ulaşıldı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
                    
                elif current_price >= self.take_profit:
                    # Take-profit seviyesine ulaşıldı, pozisyonu kapat
                    result.update({
                        'signal': 'SELL',
                        'side': 'LONG',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (current_price - self.entry_price) / self.entry_price * 100,
                        'reason': 'Take-profit seviyesine ulaşıldı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
            
            elif self.current_position == 'short':
                if indicator_signal['signal'] == 'BUY':
                    # Trendde değişim, short pozisyonu kapat
                    result.update({
                        'signal': 'BUY',
                        'side': 'SHORT',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (self.entry_price - current_price) / self.entry_price * 100,
                        'reason': 'Trend değişimi: Yukarı trendin başlangıcı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
                    
                elif current_price >= self.stop_loss:
                    # Stop-loss seviyesine ulaşıldı, pozisyonu kapat
                    result.update({
                        'signal': 'BUY',
                        'side': 'SHORT',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (self.entry_price - current_price) / self.entry_price * 100,
                        'reason': 'Stop-loss seviyesine ulaşıldı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
                    
                elif current_price <= self.take_profit:
                    # Take-profit seviyesine ulaşıldı, pozisyonu kapat
                    result.update({
                        'signal': 'BUY',
                        'side': 'SHORT',
                        'action': 'EXIT',
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'profit_loss': (self.entry_price - current_price) / self.entry_price * 100,
                        'reason': 'Take-profit seviyesine ulaşıldı'
                    })
                    
                    # Pozisyonu sıfırla
                    self._reset_position()
        
        return result
    
    def _reset_position(self) -> None:
        """
        Pozisyon durumunu sıfırlar.
        """
        self.current_position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
    
    def get_current_position(self) -> Dict[str, Any]:
        """
        Mevcut pozisyon bilgisini döndürür.
        
        Returns:
            Dict[str, Any]: Pozisyon bilgisi
        """
        if self.current_position is None:
            return {
                'position': None,
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None
            }
        
        return {
            'position': self.current_position,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }
    
    def backtest(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Stratejiyi verilen tarihsel veri üzerinde test eder.
        
        Args:
            data: Tarihsel OHLCV verileri
            
        Returns:
            Dict[str, Any]: Backtest sonuçları
        """
        if data.empty:
            logger.warning("Backtest için veri yok")
            return {'success': False, 'reason': 'Veri yok'}
        
        # Pozisyonu sıfırla
        self._reset_position()
        self.signals = []
        
        # Strateji sonuçlarını saklamak için DataFrame
        results = []
        
        # Her bar için stratejiyi çalıştır
        for i in range(self.left_bars + self.right_bars + 10, len(data)):
            # O ana kadar olan verileri al
            current_data = data.iloc[:i+1].copy()
            
            # Stratejiyi güncelle ve sinyal al
            signal = self.update(current_data)
            
            # Sonucu kaydet
            if signal['action'] != 'HOLD' or signal['signal'] != 'NEUTRAL':
                signal_data = {
                    'date': current_data.index[-1],
                    'price': current_data['close'].iloc[-1],
                    **signal
                }
                results.append(signal_data)
        
        # Backtest sonuçlarını hesapla
        summary = self._calculate_backtest_summary(results, data)
        
        return {
            'success': True,
            'signals': results,
            'summary': summary
        }
    
    def _calculate_backtest_summary(self, results: List[Dict[str, Any]], data: pd.DataFrame) -> Dict[str, Any]:
        """
        Backtest sonuçlarını özetler.
        
        Args:
            results: İşlem sinyalleri listesi
            data: Tarihsel OHLCV verileri
            
        Returns:
            Dict[str, Any]: Backtest özeti
        """
        if not results:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_return': 0,
                'max_drawdown': 0
            }
        
        # Sonuçları analiz et
        total_trades = sum(1 for r in results if r['action'] == 'EXIT')
        winning_trades = sum(1 for r in results if r['action'] == 'EXIT' and r.get('profit_loss', 0) > 0)
        
        if total_trades > 0:
            win_rate = winning_trades / total_trades * 100
        else:
            win_rate = 0
        
        # Toplam kâr ve zarar
        total_profit = sum(r.get('profit_loss', 0) for r in results if r['action'] == 'EXIT' and r.get('profit_loss', 0) > 0)
        total_loss = sum(abs(r.get('profit_loss', 0)) for r in results if r['action'] == 'EXIT' and r.get('profit_loss', 0) < 0)
        
        if total_loss > 0:
            profit_factor = total_profit / total_loss
        else:
            profit_factor = float('inf') if total_profit > 0 else 0
        
        # Toplam getiri
        total_return = sum(r.get('profit_loss', 0) for r in results if r['action'] == 'EXIT')
        
        # Maksimum drawdown hesapla
        max_drawdown = 0
        peak = 0
        equity = 100  # Başlangıç sermayesi (yüzde olarak)
        
        for r in results:
            if r['action'] == 'EXIT':
                equity += r.get('profit_loss', 0)
                
                if equity > peak:
                    peak = equity
                
                drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'max_drawdown': max_drawdown
        } 
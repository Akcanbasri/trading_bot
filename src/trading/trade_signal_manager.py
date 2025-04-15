"""
Trade Signal Manager module.

Bu modül, farklı göstergelerden gelen sinyalleri yönetir ve
işlem kararlarını verir. Aynı anda sadece bir açık pozisyon
olmasını sağlayan pozisyon kontrolü içerir.
"""
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
import time
import json
from datetime import datetime
import pandas as pd
from loguru import logger

from src.indicators.base_indicator import BaseIndicator
from src.api.binance_client import BinanceClient


class SignalType(Enum):
    """İşlem sinyali tipleri."""
    LONG = "LONG"  # Alış (Long) sinyali
    SHORT = "SHORT"  # Satış (Short) sinyali
    CLOSE_LONG = "CLOSE_LONG"  # Long pozisyon kapatma sinyali
    CLOSE_SHORT = "CLOSE_SHORT"  # Short pozisyon kapatma sinyali
    NEUTRAL = "NEUTRAL"  # Tarafsız (işlem yapma) sinyali


class PositionType(Enum):
    """Açık pozisyon tipleri."""
    LONG = "LONG"  # Long pozisyon
    SHORT = "SHORT"  # Short pozisyon
    NONE = "NONE"  # Pozisyon yok


class TradeSignalManager:
    """
    Farklı göstergelerden gelen ticaret sinyallerini yöneten ve
    işlem kararları veren sınıf.
    """

    def __init__(
        self,
        client: BinanceClient,
        symbol: str,
        indicators: Dict[str, BaseIndicator],
        notification_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        min_signal_agreement: int = 1,
        enabled: bool = True
    ):
        """
        TradeSignalManager sınıfını başlatır.

        Args:
            client: Binance API client
            symbol: İşlem yapılacak sembol (ör. BTCUSDT)
            indicators: Kullanılacak göstergelerin adları ve nesneleri
            notification_callback: İşlem açıldığında çağrılacak bildirim fonksiyonu
            min_signal_agreement: İşlem kararı için gereken minimum gösterge uyumu sayısı
            enabled: Sinyallerin işlem yaratıp yaratmayacağı
        """
        self.client = client
        self.symbol = symbol
        self.indicators = indicators
        self.notification_callback = notification_callback
        self.min_signal_agreement = min_signal_agreement
        self.enabled = enabled
        
        # Şu anki pozisyon durumu
        self.current_position = PositionType.NONE
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        
        # Son sinyaller
        self.last_signals: Dict[str, SignalType] = {}
        self.combined_signal = SignalType.NEUTRAL
        
        # İşlem geçmişi
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info(f"{symbol} için TradeSignalManager başlatıldı, {len(indicators)} gösterge kullanılıyor")
    
    def update(self, data: pd.DataFrame) -> SignalType:
        """
        Tüm göstergeleri günceller ve kombinasyon sinyalini hesaplar.
        
        Args:
            data: Fiyat verisi DataFrame'i
            
        Returns:
            SignalType: Hesaplanan kombine sinyal tipi
        """
        if data.empty:
            logger.warning("Boş veri ile güncelleme yapılamaz")
            return SignalType.NEUTRAL
        
        # Tüm göstergeleri güncelle ve sinyallerini al
        signal_counts = {
            SignalType.LONG: 0,
            SignalType.SHORT: 0,
            SignalType.CLOSE_LONG: 0,
            SignalType.CLOSE_SHORT: 0,
            SignalType.NEUTRAL: 0
        }
        
        for name, indicator in self.indicators.items():
            try:
                # Göstergeyi güncelle
                indicator.update(data)
                
                # Sinyal tipini belirle
                signal = self._get_signal_from_indicator(name, indicator)
                
                # Sinyal sayısını artır
                signal_counts[signal] += 1
                
                # Son sinyalleri güncelle
                self.last_signals[name] = signal
                
                logger.debug(f"{name} göstergesi sinyali: {signal.value}")
            except Exception as e:
                logger.error(f"{name} göstergesi güncellenirken hata oluştu: {e}")
        
        # Kombine sinyali hesapla
        combined_signal = self._calculate_combined_signal(signal_counts)
        self.combined_signal = combined_signal
        
        # Pozisyon kontrolü ve işlem kararı
        if self.enabled:
            self._process_signal(combined_signal)
        
        return combined_signal
    
    def _get_signal_from_indicator(self, name: str, indicator: BaseIndicator) -> SignalType:
        """
        Bir göstergeden sinyal tipini belirler.
        
        Args:
            name: Gösterge adı
            indicator: Gösterge nesnesi
            
        Returns:
            SignalType: Göstergenin ürettiği sinyal tipi
        """
        # RSI Middle Band göstergesi için özel kontrol
        if "rsi_middle_band" in name.lower():
            # RSIMiddleBand sınıfından bir nesne ise
            if hasattr(indicator, "is_buy_signal") and hasattr(indicator, "is_sell_signal"):
                if indicator.is_buy_signal():
                    return SignalType.LONG
                elif indicator.is_sell_signal():
                    return SignalType.SHORT
        
        # Genel göstergeler için sinyal kontrolü
        signal_info = indicator.get_signal()
        signal_value = signal_info.get("signal", "NEUTRAL")
        
        if signal_value == "BUY":
            return SignalType.LONG
        elif signal_value == "SELL":
            return SignalType.SHORT
        elif signal_value == "CLOSE_LONG":
            return SignalType.CLOSE_LONG
        elif signal_value == "CLOSE_SHORT":
            return SignalType.CLOSE_SHORT
        else:
            return SignalType.NEUTRAL
    
    def _calculate_combined_signal(self, signal_counts: Dict[SignalType, int]) -> SignalType:
        """
        Tüm göstergelerin sinyallerinden bir kombine sinyal hesaplar.
        
        Args:
            signal_counts: Her sinyal tipinden kaç tane olduğu
            
        Returns:
            SignalType: Hesaplanan kombine sinyal
        """
        # Şu anki pozisyona göre kapatma sinyallerini kontrol et
        if self.current_position == PositionType.LONG and signal_counts[SignalType.CLOSE_LONG] >= self.min_signal_agreement:
            return SignalType.CLOSE_LONG
        
        if self.current_position == PositionType.SHORT and signal_counts[SignalType.CLOSE_SHORT] >= self.min_signal_agreement:
            return SignalType.CLOSE_SHORT
        
        # Yeni pozisyon için sinyalleri kontrol et
        if signal_counts[SignalType.LONG] >= self.min_signal_agreement:
            if self.current_position == PositionType.NONE:
                return SignalType.LONG
            elif self.current_position == PositionType.SHORT:
                return SignalType.CLOSE_SHORT  # Önce mevcut pozisyonu kapat
        
        if signal_counts[SignalType.SHORT] >= self.min_signal_agreement:
            if self.current_position == PositionType.NONE:
                return SignalType.SHORT
            elif self.current_position == PositionType.LONG:
                return SignalType.CLOSE_LONG  # Önce mevcut pozisyonu kapat
        
        # Yeterli sinyal yoksa nötr kal
        return SignalType.NEUTRAL
    
    def _process_signal(self, signal: SignalType) -> None:
        """
        Bir sinyali işler ve gerekli işlemleri gerçekleştirir.
        
        Args:
            signal: İşlenecek sinyal tipi
        """
        # Mevcut fiyatı al
        current_price = self._get_current_price()
        if not current_price:
            logger.error("Fiyat bilgisi alınamadı, işlem yapılamıyor")
            return
        
        # Pozisyon kontrolü ve işlem kararları
        if signal == SignalType.LONG and self.current_position == PositionType.NONE:
            # Long pozisyon aç
            self._open_position(PositionType.LONG, current_price)
            
        elif signal == SignalType.SHORT and self.current_position == PositionType.NONE:
            # Short pozisyon aç
            self._open_position(PositionType.SHORT, current_price)
            
        elif signal == SignalType.CLOSE_LONG and self.current_position == PositionType.LONG:
            # Long pozisyonu kapat
            self._close_position(current_price)
            
        elif signal == SignalType.CLOSE_SHORT and self.current_position == PositionType.SHORT:
            # Short pozisyonu kapat
            self._close_position(current_price)
    
    def _open_position(self, position_type: PositionType, price: float) -> None:
        """
        Yeni bir pozisyon açar.
        
        Args:
            position_type: Açılacak pozisyon tipi (LONG/SHORT)
            price: Giriş fiyatı
        """
        if self.current_position != PositionType.NONE:
            logger.warning(f"Zaten açık bir pozisyon var: {self.current_position.value}")
            return
        
        try:
            # Hesap bakiyesini kontrol et ve pozisyon büyüklüğünü hesapla
            account_balance = self._get_usdt_balance()
            if not account_balance:
                logger.error("Hesap bakiyesi alınamadı")
                return
            
            # Hesap bakiyesinin %1'i kadar pozisyon aç (örnek)
            position_percentage = 0.01  # %1
            position_size_usdt = account_balance * position_percentage
            
            # USDT tutarını coin miktarına dönüştür
            position_size = position_size_usdt / price
            
            # Binance'e emir gönder
            side = "BUY" if position_type == PositionType.LONG else "SELL"
            logger.info(f"{side} emri gönderiliyor: {position_size} {self.symbol} @ {price}")
            
            # Gerçek API çağrısı
            order = self.client.create_market_order(
                symbol=self.symbol,
                side=side,
                quantity=position_size
            )
            
            # Pozisyon bilgilerini güncelle
            self.current_position = position_type
            self.position_size = position_size
            self.entry_price = price
            self.entry_time = datetime.now()
            
            # İşlem bilgilerini hazırla
            trade_info = {
                "type": "OPEN",
                "position": position_type.value,
                "symbol": self.symbol,
                "size": position_size,
                "price": price,
                "time": self.entry_time.isoformat(),
                "order_id": order.get("orderId", "unknown"),
                "signals": {name: signal.value for name, signal in self.last_signals.items()}
            }
            
            # İşlem geçmişine ekle
            self.trade_history.append(trade_info)
            
            # Log ve bildirim
            logger.info(f"Pozisyon açıldı: {position_type.value} {position_size} {self.symbol} @ {price}")
            self._notify_trade(trade_info)
            
        except Exception as e:
            logger.error(f"Pozisyon açılırken hata oluştu: {e}")
    
    def _close_position(self, price: float) -> None:
        """
        Mevcut pozisyonu kapatır.
        
        Args:
            price: Çıkış fiyatı
        """
        if self.current_position == PositionType.NONE:
            logger.warning("Kapatılacak pozisyon yok")
            return
        
        try:
            # Binance'e emir gönder
            side = "SELL" if self.current_position == PositionType.LONG else "BUY"
            logger.info(f"{side} emri gönderiliyor: {self.position_size} {self.symbol} @ {price}")
            
            # Gerçek API çağrısı
            order = self.client.create_market_order(
                symbol=self.symbol,
                side=side,
                quantity=self.position_size
            )
            
            # Kar/Zarar hesapla
            pnl = 0.0
            if self.current_position == PositionType.LONG:
                pnl = (price - self.entry_price) * self.position_size
            else:
                pnl = (self.entry_price - price) * self.position_size
            
            pnl_percentage = (pnl / (self.entry_price * self.position_size)) * 100
            
            # İşlem bilgilerini hazırla
            trade_info = {
                "type": "CLOSE",
                "position": self.current_position.value,
                "symbol": self.symbol,
                "size": self.position_size,
                "entry_price": self.entry_price,
                "exit_price": price,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "time": datetime.now().isoformat(),
                "duration": (datetime.now() - self.entry_time).total_seconds() if self.entry_time else 0,
                "order_id": order.get("orderId", "unknown"),
                "signals": {name: signal.value for name, signal in self.last_signals.items()}
            }
            
            # İşlem geçmişine ekle
            self.trade_history.append(trade_info)
            
            # Log ve bildirim
            logger.info(f"Pozisyon kapatıldı: {self.current_position.value} {self.position_size} {self.symbol}, " 
                         f"PNL: {pnl:.2f} USDT ({pnl_percentage:.2f}%)")
            self._notify_trade(trade_info)
            
            # Pozisyon durumunu sıfırla
            self.current_position = PositionType.NONE
            self.position_size = 0.0
            self.entry_price = 0.0
            self.entry_time = None
            
        except Exception as e:
            logger.error(f"Pozisyon kapatılırken hata oluştu: {e}")
    
    def _get_current_price(self) -> Optional[float]:
        """
        Mevcut fiyatı alır.
        
        Returns:
            float: Mevcut fiyat
        """
        try:
            ticker = self.client._public_request("GET", "/api/v3/ticker/price", {"symbol": self.symbol})
            return float(ticker["price"])
        except Exception as e:
            logger.error(f"Fiyat alınırken hata oluştu: {e}")
            return None
    
    def _get_usdt_balance(self) -> Optional[float]:
        """
        USDT bakiyesini alır.
        
        Returns:
            float: USDT bakiyesi
        """
        try:
            balance = self.client.get_asset_balance("USDT")
            return balance["free"]
        except Exception as e:
            logger.error(f"USDT bakiyesi alınırken hata oluştu: {e}")
            return None
    
    def _notify_trade(self, trade_info: Dict[str, Any]) -> None:
        """
        İşlem bilgilerini bildirim fonksiyonuna gönderir.
        
        Args:
            trade_info: İşlem bilgileri
        """
        if self.notification_callback:
            try:
                self.notification_callback(trade_info)
            except Exception as e:
                logger.error(f"Bildirim gönderilirken hata oluştu: {e}")
        
        # Loglamayı da burada yapabiliriz
        log_message = json.dumps(trade_info, indent=2)
        logger.info(f"İşlem gerçekleşti:\n{log_message}")
    
    def get_position_status(self) -> Dict[str, Any]:
        """
        Mevcut pozisyon durumunu döndürür.
        
        Returns:
            Dict: Pozisyon durumu bilgileri
        """
        return {
            "symbol": self.symbol,
            "position": self.current_position.value,
            "size": self.position_size,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "current_price": self._get_current_price(),
            "last_signal": self.combined_signal.value,
            "indicator_signals": {name: signal.value for name, signal in self.last_signals.items()}
        }
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """
        İşlem geçmişini döndürür.
        
        Returns:
            List[Dict]: İşlem geçmişi
        """
        return self.trade_history
    
    def enable(self) -> None:
        """Sinyal yöneticisini etkinleştirir."""
        self.enabled = True
        logger.info(f"{self.symbol} için sinyal yöneticisi etkinleştirildi")
    
    def disable(self) -> None:
        """Sinyal yöneticisini devre dışı bırakır."""
        self.enabled = False
        logger.info(f"{self.symbol} için sinyal yöneticisi devre dışı bırakıldı") 
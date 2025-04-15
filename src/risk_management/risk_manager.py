"""
Risk yönetimi modülü.
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from loguru import logger
import os
from dotenv import load_dotenv


class RiskManager:
    """
    Trading işlemlerinde risk yönetimini sağlayan sınıf.
    """
    
    def __init__(self):
        """Risk yöneticisini başlatır."""
        load_dotenv()
        
        # Temel risk parametreleri
        self.min_position_size_usd = float(os.getenv('MIN_POSITION_SIZE_USD', 5.0))
        self.max_open_trades = int(os.getenv('MAX_OPEN_POSITIONS', 2))
        self.max_position_size_usd = float(os.getenv('MAX_POSITION_SIZE_USD', 50.0))
        self.max_position_size_percent = float(os.getenv('MAX_POSITION_SIZE_PERCENTAGE', 3.0))
        self.max_daily_loss_percent = float(os.getenv('MAX_DAILY_LOSS_PERCENTAGE', 3.0))
        self.max_total_loss_percent = float(os.getenv('MAX_TOTAL_LOSS_PERCENTAGE', 15.0))
        self.stop_loss_percent = float(os.getenv('DEFAULT_STOP_LOSS_PERCENTAGE', 1.5))
        self.take_profit_percent = float(os.getenv('DEFAULT_TAKE_PROFIT_PERCENTAGE', 3.0))
        self.risk_reward_ratio = float(os.getenv('RISK_REWARD_RATIO', 2.0))
        
        # Futures özel parametreleri
        self.leverage_mode = os.getenv('LEVERAGE_MODE', 'cross')
        self.default_leverage = int(os.getenv('DEFAULT_LEVERAGE', 5))
        self.max_leverage = int(os.getenv('MAX_LEVERAGE', 10))
        self.liquidation_buffer = float(os.getenv('LIQUIDATION_BUFFER_PERCENTAGE', 50.0))
        self.enable_partial_close = os.getenv('ENABLE_PARTIAL_CLOSE', 'true').lower() == 'true'
        self.partial_close_percent = float(os.getenv('PARTIAL_CLOSE_PERCENTAGE', 50.0))
        self.enable_breakeven = os.getenv('ENABLE_BREAKEVEN', 'true').lower() == 'true'
        self.breakeven_trigger = float(os.getenv('BREAKEVEN_TRIGGER_PERCENTAGE', 1.0))
        
        # Trailing stop parametreleri
        self.enable_trailing_stop = os.getenv('ENABLE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_stop_activation = float(os.getenv('TRAILING_STOP_ACTIVATION_PERCENTAGE', 0.8))
        self.trailing_stop_callback = float(os.getenv('TRAILING_STOP_CALLBACK_PERCENTAGE', 0.3))
        
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: float = 0.0
        self.total_balance: float = 0.0
        self.available_balance: float = 0.0
        
        logger.info(f"Risk yöneticisi başlatıldı. Futures modu aktif.")
    
    def set_balance(self, total: float, available: float) -> None:
        """
        Bakiye bilgisini ayarlar.
        
        Args:
            total: Toplam bakiye
            available: Kullanılabilir bakiye
        """
        self.total_balance = total
        self.available_balance = available
        logger.debug(f"Bakiye güncellendi. Toplam: {total}, Kullanılabilir: {available}")
    
    def can_open_new_position(self, symbol: str, side: str) -> bool:
        """
        Yeni bir pozisyon açılıp açılamayacağını kontrol eder.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            
        Returns:
            bool: Pozisyon açılabilirse True, aksi halde False
        """
        # Açık pozisyon sayısı kontrolü
        if len(self.open_positions) >= self.max_open_trades and symbol not in self.open_positions:
            logger.warning(f"Maksimum açık pozisyon sayısı ({self.max_open_trades}) aşıldı")
            return False
        
        # Günlük kayıp limiti kontrolü
        if self.daily_pnl < -(self.total_balance * self.max_daily_loss_percent / 100):
            logger.warning(f"Günlük kayıp limiti (-%{self.max_daily_loss_percent}) aşıldı")
            return False
        
        # Minimum işlem büyüklüğü kontrolü
        if self.available_balance < self.min_position_size_usd:
            logger.warning(f"Kullanılabilir bakiye ({self.available_balance} USDT) minimum işlem büyüklüğünden ({self.min_position_size_usd} USDT) küçük")
            return False
        
        # Aynı sembol için ters pozisyon kontrolü (opsiyonel)
        if symbol in self.open_positions and self.open_positions[symbol]["side"] != side:
            # Ters pozisyon olabilir, pozisyonu kapatıyor olabilir
            return True
        
        return True
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        leverage: int
    ) -> float:
        """
        Futures pozisyon boyutunu hesaplar.
        
        Args:
            symbol: İşlem sembolü
            entry_price: Giriş fiyatı
            stop_loss: Stop-loss fiyatı
            leverage: Kaldıraç oranı
            
        Returns:
            float: Pozisyon boyutu (kontrat sayısı)
        """
        # Risk miktarını hesapla (USDT)
        risk_amount = min(
            self.max_position_size_usd,
            self.total_balance * (self.max_position_size_percent / 100)
        )
        
        # Minimum işlem büyüklüğü kontrolü
        if risk_amount < self.min_position_size_usd:
            logger.warning(f"Hesaplanan risk miktarı ({risk_amount} USDT) minimum işlem büyüklüğünden ({self.min_position_size_usd} USDT) küçük")
            return 0.0
        
        # Stop-loss mesafesi
        stop_distance = abs(entry_price - stop_loss)
        stop_distance_percent = (stop_distance / entry_price) * 100
        
        # Kaldıraçlı risk hesaplama
        leveraged_risk = risk_amount * leverage
        
        # Kontrat sayısını hesapla
        position_size = leveraged_risk / stop_distance
        
        # Likidasyon mesafesini kontrol et
        liquidation_price = self.calculate_liquidation_price(
            symbol, entry_price, position_size, leverage
        )
        
        if abs(entry_price - liquidation_price) < stop_distance:
            # Likidasyon riski var, pozisyon boyutunu düşür
            position_size = position_size * (self.liquidation_buffer / 100)
            
            # Minimum işlem büyüklüğü kontrolü
            if position_size * entry_price < self.min_position_size_usd:
                logger.warning(f"Düşürülen pozisyon boyutu ({position_size * entry_price} USDT) minimum işlem büyüklüğünden ({self.min_position_size_usd} USDT) küçük")
                return 0.0
            
        return position_size
    
    def calculate_liquidation_price(
        self,
        symbol: str,
        entry_price: float,
        position_size: float,
        leverage: int
    ) -> float:
        """
        Likidasyon fiyatını hesaplar.
        
        Args:
            symbol: İşlem sembolü
            entry_price: Giriş fiyatı
            position_size: Pozisyon boyutu
            leverage: Kaldıraç oranı
            
        Returns:
            float: Likidasyon fiyatı
        """
        # Basit likidasyon hesaplaması
        maintenance_margin = 0.004  # %0.4 bakım marjı
        position_value = position_size * entry_price
        margin = position_value / leverage
        
        if position_size > 0:  # Long pozisyon
            return entry_price * (1 - (1 / leverage) + maintenance_margin)
        else:  # Short pozisyon
            return entry_price * (1 + (1 / leverage) - maintenance_margin)
    
    def calculate_take_profit(
        self, 
        symbol: str, 
        side: str, 
        entry_price: float,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Take-profit seviyesini hesaplar.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            entry_price: Giriş fiyatı
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            float: Take-profit fiyatı
        """
        # Özel take profit değeri varsa kullan
        take_profit_percent = self.take_profit_percent
        
        if signal_data and "take_profit_percent" in signal_data:
            take_profit_percent = signal_data["take_profit_percent"]
        
        # Take profit hesaplama
        take_profit = entry_price * (1 + take_profit_percent / 100) if side == "BUY" else entry_price * (1 - take_profit_percent / 100)
        
        logger.debug(f"{symbol} için take-profit: {take_profit} (%{take_profit_percent})")
        return take_profit
    
    def calculate_stop_loss(
        self, 
        symbol: str, 
        side: str, 
        entry_price: float,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Stop-loss seviyesini hesaplar.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            entry_price: Giriş fiyatı
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            float: Stop-loss fiyatı
        """
        # Özel stop loss değeri varsa kullan
        stop_loss_percent = self.stop_loss_percent
        
        if signal_data and "stop_loss_percent" in signal_data:
            stop_loss_percent = signal_data["stop_loss_percent"]
        
        # Stop loss hesaplama
        stop_loss = entry_price * (1 - stop_loss_percent / 100) if side == "BUY" else entry_price * (1 + stop_loss_percent / 100)
        
        logger.debug(f"{symbol} için stop-loss: {stop_loss} (%{stop_loss_percent})")
        return stop_loss
    
    def record_trade(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float,
        trade_type: str = "MARKET"
    ) -> None:
        """
        Gerçekleşen bir işlemi kaydeder.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            price: İşlem fiyatı
            trade_type: İşlem tipi ("MARKET" veya "LIMIT")
        """
        trade = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "type": trade_type,
            "time": datetime.now().isoformat(),
            "value": quantity * price
        }
        
        # İşlem geçmişine ekle
        self.trade_history.append(trade)
        
        # Açık pozisyonları güncelle
        if side == "BUY":
            if symbol in self.open_positions:
                # Mevcut pozisyonu güncelle
                current = self.open_positions[symbol]
                total_qty = current["quantity"] + quantity
                avg_price = ((current["quantity"] * current["price"]) + (quantity * price)) / total_qty
                
                self.open_positions[symbol].update({
                    "quantity": total_qty,
                    "price": avg_price,
                    "last_update": datetime.now().isoformat()
                })
            else:
                # Yeni pozisyon ekle
                self.open_positions[symbol] = {
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": quantity,
                    "price": price,
                    "time": datetime.now().isoformat(),
                    "last_update": datetime.now().isoformat(),
                    "stop_loss": self.calculate_stop_loss(symbol, "BUY", price),
                    "take_profit": self.calculate_take_profit(symbol, "BUY", price)
                }
        elif side == "SELL":
            if symbol in self.open_positions:
                # Pozisyonu güncelle veya kapat
                current = self.open_positions[symbol]
                
                if quantity >= current["quantity"]:
                    # Pozisyonu kapat ve kar/zarar hesapla
                    pnl = (price - current["price"]) * current["quantity"] if current["side"] == "BUY" else (current["price"] - price) * current["quantity"]
                    self.daily_pnl += pnl
                    
                    # Pozisyonu kaldır
                    self.position_closed(symbol)
                else:
                    # Pozisyonu kısmen kapat
                    current["quantity"] -= quantity
                    current["last_update"] = datetime.now().isoformat()
            else:
                # Short pozisyon aç
                self.open_positions[symbol] = {
                    "symbol": symbol,
                    "side": "SELL",
                    "quantity": quantity,
                    "price": price,
                    "time": datetime.now().isoformat(),
                    "last_update": datetime.now().isoformat(),
                    "stop_loss": self.calculate_stop_loss(symbol, "SELL", price),
                    "take_profit": self.calculate_take_profit(symbol, "SELL", price)
                }
        
        logger.info(f"İşlem kaydedildi: {side} {quantity} {symbol} @ {price}")
    
    def position_closed(self, symbol: str) -> None:
        """
        Bir pozisyonun kapandığını kaydeder.
        
        Args:
            symbol: İşlem sembolü
        """
        if symbol in self.open_positions:
            del self.open_positions[symbol]
            logger.info(f"{symbol} pozisyonu kapatıldı")
    
    def get_open_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Açık pozisyonları döndürür.
        
        Returns:
            Dict: Açık pozisyonlar
        """
        return self.open_positions
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """
        İşlem geçmişini döndürür.
        
        Returns:
            List: İşlem geçmişi
        """
        return self.trade_history
    
    def reset_daily_stats(self) -> None:
        """
        Günlük istatistikleri sıfırlar.
        """
        self.daily_pnl = 0.0
        logger.info("Günlük istatistikler sıfırlandı")
    
    def update_position_status(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Bir pozisyonun durumunu günceller ve gerekirse stop-loss/take-profit kontrolü yapar.
        
        Args:
            symbol: İşlem sembolü
            current_price: Güncel fiyat
            
        Returns:
            Dict: Pozisyon durumu bilgisi
        """
        if symbol not in self.open_positions:
            return {"status": "NO_POSITION", "symbol": symbol}
        
        position = self.open_positions[symbol]
        entry_price = position["price"]
        position_side = position["side"]
        
        # Kar/zarar hesapla
        if position_side == "BUY":
            pnl_percent = (current_price - entry_price) / entry_price * 100
            unrealized_pnl = (current_price - entry_price) * position["quantity"]
        else:  # SELL (Short)
            pnl_percent = (entry_price - current_price) / entry_price * 100
            unrealized_pnl = (entry_price - current_price) * position["quantity"]
        
        # Pozisyon durumunu güncelle
        position_status = {
            "symbol": symbol,
            "side": position_side,
            "entry_price": entry_price,
            "current_price": current_price,
            "pnl_percent": pnl_percent,
            "unrealized_pnl": unrealized_pnl,
            "stop_loss_hit": False,
            "take_profit_hit": False
        }
        
        # Stop-loss kontrolü
        if position_side == "BUY" and current_price <= position["stop_loss"]:
            position_status["stop_loss_hit"] = True
        elif position_side == "SELL" and current_price >= position["stop_loss"]:
            position_status["stop_loss_hit"] = True
        
        # Take-profit kontrolü
        if position_side == "BUY" and current_price >= position["take_profit"]:
            position_status["take_profit_hit"] = True
        elif position_side == "SELL" and current_price <= position["take_profit"]:
            position_status["take_profit_hit"] = True
        
        return position_status
    
    def should_move_to_breakeven(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        position_side: str
    ) -> bool:
        """
        Breakeven noktasına geçilip geçilmeyeceğini kontrol eder.
        
        Args:
            symbol: İşlem sembolü
            entry_price: Giriş fiyatı
            current_price: Mevcut fiyat
            position_side: Pozisyon yönü ('LONG' veya 'SHORT')
            
        Returns:
            bool: Breakeven'e geçilmeli ise True
        """
        if not self.enable_breakeven:
            return False
            
        price_change_percent = abs(current_price - entry_price) / entry_price * 100
        
        if position_side == 'LONG':
            return price_change_percent >= self.breakeven_trigger
        else:
            return price_change_percent >= self.breakeven_trigger
            
    def should_partial_close(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        position_side: str
    ) -> bool:
        """
        Kısmi kapanış yapılıp yapılmayacağını kontrol eder.
        
        Args:
            symbol: İşlem sembolü
            entry_price: Giriş fiyatı
            current_price: Mevcut fiyat
            position_side: Pozisyon yönü ('LONG' veya 'SHORT')
            
        Returns:
            bool: Kısmi kapanış yapılmalı ise True
        """
        if not self.enable_partial_close:
            return False
            
        price_change_percent = abs(current_price - entry_price) / entry_price * 100
        
        if position_side == 'LONG':
            return price_change_percent >= (self.take_profit_percent * self.partial_close_percent / 100)
        else:
            return price_change_percent >= (self.take_profit_percent * self.partial_close_percent / 100)
            
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        position_side: str
    ) -> Optional[float]:
        """
        Trailing stop seviyesini günceller.
        
        Args:
            symbol: İşlem sembolü
            current_price: Mevcut fiyat
            position_side: Pozisyon yönü ('LONG' veya 'SHORT')
            
        Returns:
            Optional[float]: Yeni stop-loss seviyesi
        """
        if not self.enable_trailing_stop or symbol not in self.open_positions:
            return None
            
        position = self.open_positions[symbol]
        entry_price = position['entry_price']
        current_stop = position.get('stop_loss')
        
        price_change_percent = abs(current_price - entry_price) / entry_price * 100
        
        if price_change_percent < self.trailing_stop_activation:
            return None
            
        if position_side == 'LONG':
            new_stop = current_price * (1 - self.trailing_stop_callback / 100)
            if not current_stop or new_stop > current_stop:
                return new_stop
        else:
            new_stop = current_price * (1 + self.trailing_stop_callback / 100)
            if not current_stop or new_stop < current_stop:
                return new_stop
                
        return None 
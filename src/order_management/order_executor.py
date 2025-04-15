"""
Emir yürütme ve yönetim modülü.
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from loguru import logger
import os

from src.api.client import BinanceClient
from src.risk_management.risk_manager import RiskManager
from src.notifications.telegram_notifier import TelegramNotifier


class OrderExecutor:
    """
    Alım/satım emirlerini yürüten ve yöneten sınıf.
    """
    
    def __init__(self, client: BinanceClient, risk_manager: RiskManager):
        """
        OrderExecutor sınıfını başlatır.
        
        Args:
            client: Binance API istemcisi
            risk_manager: Risk yönetim sınıfı
        """
        self.client = client
        self.risk_manager = risk_manager
        self.orders: List[Dict[str, Any]] = []
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # Telegram bildirimleri için
        telegram_enabled = os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "false").lower() == "true"
        if telegram_enabled:
            self.notifier = TelegramNotifier(
                bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
                chat_id=os.getenv("TELEGRAM_CHAT_ID")
            )
        else:
            self.notifier = None
        
        logger.info("Emir yürütücüsü başlatıldı")
    
    def get_symbol_quantity(
        self, 
        symbol: str, 
        side: str, 
        price: Optional[float] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Risk yöneticisini kullanarak işlem için uygun miktarı belirler.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            price: İşlem fiyatı (opsiyonel)
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            float: İşlem miktarı
        """
        # Mevcut fiyatı al eğer verilmediyse
        if price is None:
            try:
                price = self.client.get_current_price(symbol)
            except Exception as e:
                logger.error(f"{symbol} için güncel fiyat alınamadı: {e}")
                return 0.0
        
        # Risk yöneticisini kullanarak işlem miktarını belirle
        quantity = self.risk_manager.calculate_position_size(
            symbol=symbol,
            side=side,
            price=price,
            signal_data=signal_data
        )
        
        return quantity
    
    def create_market_buy_order(
        self, 
        symbol: str, 
        quantity: Optional[float] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Piyasa fiyatından alım emri oluşturur.
        
        Args:
            symbol: İşlem sembolü
            quantity: İşlem miktarı (None ise risk yöneticisi hesaplar)
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            Dict: Oluşturulan emir bilgisi
        """
        try:
            # Risk kontrolü yap
            if not self.risk_manager.can_open_new_position(symbol, "BUY"):
                logger.warning(f"{symbol} için alım pozisyonu açılamaz - risk limiti aşılmış")
                return {"error": "Risk limiti aşıldı", "symbol": symbol, "side": "BUY"}
            
            # İşlem miktarını belirle
            if quantity is None:
                quantity = self.get_symbol_quantity(
                    symbol=symbol,
                    side="BUY",
                    signal_data=signal_data
                )
            
            if quantity <= 0:
                logger.warning(f"{symbol} için hesaplanan miktar geçersiz: {quantity}")
                return {"error": "Geçersiz miktar", "symbol": symbol, "side": "BUY"}
            
            # Emir oluştur
            order = self.client.create_order(
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quantity=quantity
            )
            
            # Emir bilgisini kaydet
            order_info = {
                "order_id": order["orderId"],
                "symbol": symbol,
                "side": "BUY",
                "type": "MARKET",
                "quantity": float(quantity),
                "price": float(order.get("price", 0)),
                "status": order["status"],
                "time": datetime.now().isoformat(),
                "signal_data": signal_data
            }
            
            self.orders.append(order_info)
            
            # Pozisyonu takip et
            if order["status"] == "FILLED":
                self._update_position(symbol, "BUY", quantity, float(order.get("price", 0)))
            
            # Telegram bildirimi gönder
            if self.notifier and order.get("status") == "FILLED":
                self.notifier.send_trade_notification(
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=float(order["price"]),
                    profit_loss=None  # İlk açılışta kar/zarar yok
                )
            
            logger.info(f"ALIM emri oluşturuldu: {symbol} - Miktar: {quantity}")
            return order_info
            
        except Exception as e:
            logger.error(f"{symbol} için alım emri oluşturulurken hata: {e}")
            return {"error": str(e), "symbol": symbol, "side": "BUY"}
    
    def create_market_sell_order(
        self, 
        symbol: str, 
        quantity: Optional[float] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Piyasa fiyatından satım emri oluşturur.
        
        Args:
            symbol: İşlem sembolü
            quantity: İşlem miktarı (None ise risk yöneticisi hesaplar)
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            Dict: Oluşturulan emir bilgisi
        """
        try:
            # Eğer miktar belirtilmediyse
            if quantity is None:
                # Açık pozisyon var mı kontrol et
                if symbol in self.positions:
                    # Tüm pozisyonu kapat
                    quantity = self.positions[symbol]["quantity"]
                else:
                    # Risk yöneticisini kullanarak hesapla
                    quantity = self.get_symbol_quantity(
                        symbol=symbol,
                        side="SELL",
                        signal_data=signal_data
                    )
            
            if quantity <= 0:
                logger.warning(f"{symbol} için hesaplanan miktar geçersiz: {quantity}")
                return {"error": "Geçersiz miktar", "symbol": symbol, "side": "SELL"}
            
            # Emir oluştur
            order = self.client.create_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=quantity
            )
            
            # Emir bilgisini kaydet
            order_info = {
                "order_id": order["orderId"],
                "symbol": symbol,
                "side": "SELL",
                "type": "MARKET",
                "quantity": float(quantity),
                "price": float(order.get("price", 0)),
                "status": order["status"],
                "time": datetime.now().isoformat(),
                "signal_data": signal_data
            }
            
            self.orders.append(order_info)
            
            # Pozisyonu takip et
            if order["status"] == "FILLED":
                self._update_position(symbol, "SELL", quantity, float(order.get("price", 0)))
            
            # Telegram bildirimi gönder
            if self.notifier and order.get("status") == "FILLED":
                self.notifier.send_trade_notification(
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    price=float(order["price"]),
                    profit_loss=None  # İlk açılışta kar/zarar yok
                )
            
            logger.info(f"SATIM emri oluşturuldu: {symbol} - Miktar: {quantity}")
            return order_info
            
        except Exception as e:
            logger.error(f"{symbol} için satım emri oluşturulurken hata: {e}")
            return {"error": str(e), "symbol": symbol, "side": "SELL"}
    
    def create_limit_buy_order(
        self, 
        symbol: str, 
        price: float,
        quantity: Optional[float] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Limit fiyatından alım emri oluşturur.
        
        Args:
            symbol: İşlem sembolü
            price: Limit fiyatı
            quantity: İşlem miktarı (None ise risk yöneticisi hesaplar)
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            Dict: Oluşturulan emir bilgisi
        """
        try:
            # Risk kontrolü yap
            if not self.risk_manager.can_open_new_position(symbol, "BUY"):
                logger.warning(f"{symbol} için alım pozisyonu açılamaz - risk limiti aşılmış")
                return {"error": "Risk limiti aşıldı", "symbol": symbol, "side": "BUY"}
            
            # İşlem miktarını belirle
            if quantity is None:
                quantity = self.get_symbol_quantity(
                    symbol=symbol,
                    side="BUY",
                    price=price,
                    signal_data=signal_data
                )
            
            if quantity <= 0:
                logger.warning(f"{symbol} için hesaplanan miktar geçersiz: {quantity}")
                return {"error": "Geçersiz miktar", "symbol": symbol, "side": "BUY"}
            
            # Emir oluştur
            order = self.client.create_order(
                symbol=symbol,
                side="BUY",
                type="LIMIT",
                timeInForce="GTC",  # Good Till Cancelled
                quantity=quantity,
                price=price
            )
            
            # Emir bilgisini kaydet
            order_info = {
                "order_id": order["orderId"],
                "symbol": symbol,
                "side": "BUY",
                "type": "LIMIT",
                "quantity": float(quantity),
                "price": float(price),
                "status": order["status"],
                "time": datetime.now().isoformat(),
                "signal_data": signal_data
            }
            
            self.orders.append(order_info)
            logger.info(f"LIMIT ALIM emri oluşturuldu: {symbol} - Fiyat: {price}, Miktar: {quantity}")
            
            # Telegram bildirimi gönder
            if self.notifier and order.get("status") == "FILLED":
                self.notifier.send_trade_notification(
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=float(order["price"]),
                    profit_loss=None  # İlk açılışta kar/zarar yok
                )
            
            return order_info
            
        except Exception as e:
            logger.error(f"{symbol} için limit alım emri oluşturulurken hata: {e}")
            return {"error": str(e), "symbol": symbol, "side": "BUY", "type": "LIMIT"}
    
    def create_limit_sell_order(
        self, 
        symbol: str, 
        price: float,
        quantity: Optional[float] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Limit fiyatından satım emri oluşturur.
        
        Args:
            symbol: İşlem sembolü
            price: Limit fiyatı
            quantity: İşlem miktarı (None ise mevcut pozisyon miktarı kullanılır)
            signal_data: Sinyal verileri (opsiyonel)
            
        Returns:
            Dict: Oluşturulan emir bilgisi
        """
        try:
            # Eğer miktar belirtilmediyse
            if quantity is None:
                # Açık pozisyon var mı kontrol et
                if symbol in self.positions:
                    # Tüm pozisyonu kapat
                    quantity = self.positions[symbol]["quantity"]
                else:
                    # Risk yöneticisini kullanarak hesapla
                    quantity = self.get_symbol_quantity(
                        symbol=symbol,
                        side="SELL",
                        price=price,
                        signal_data=signal_data
                    )
            
            if quantity <= 0:
                logger.warning(f"{symbol} için hesaplanan miktar geçersiz: {quantity}")
                return {"error": "Geçersiz miktar", "symbol": symbol, "side": "SELL"}
            
            # Emir oluştur
            order = self.client.create_order(
                symbol=symbol,
                side="SELL",
                type="LIMIT",
                timeInForce="GTC",  # Good Till Cancelled
                quantity=quantity,
                price=price
            )
            
            # Emir bilgisini kaydet
            order_info = {
                "order_id": order["orderId"],
                "symbol": symbol,
                "side": "SELL",
                "type": "LIMIT",
                "quantity": float(quantity),
                "price": float(price),
                "status": order["status"],
                "time": datetime.now().isoformat(),
                "signal_data": signal_data
            }
            
            self.orders.append(order_info)
            logger.info(f"LIMIT SATIM emri oluşturuldu: {symbol} - Fiyat: {price}, Miktar: {quantity}")
            
            # Telegram bildirimi gönder
            if self.notifier and order.get("status") == "FILLED":
                self.notifier.send_trade_notification(
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    price=float(order["price"]),
                    profit_loss=None  # İlk açılışta kar/zarar yok
                )
            
            return order_info
            
        except Exception as e:
            logger.error(f"{symbol} için limit satım emri oluşturulurken hata: {e}")
            return {"error": str(e), "symbol": symbol, "side": "SELL", "type": "LIMIT"}
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Bir emri iptal eder.
        
        Args:
            symbol: İşlem sembolü
            order_id: Emir ID'si
            
        Returns:
            Dict: İptal edilen emir bilgisi
        """
        try:
            result = self.client.cancel_order(
                symbol=symbol,
                order_id=order_id
            )
            
            # Emir listesini güncelle
            for i, order in enumerate(self.orders):
                if order.get("order_id") == order_id:
                    self.orders[i]["status"] = "CANCELED"
            
            logger.info(f"Emir iptal edildi: {symbol} - Emir ID: {order_id}")
            return result
            
        except Exception as e:
            logger.error(f"Emir iptal edilirken hata: {e}")
            return {"error": str(e), "symbol": symbol, "order_id": order_id}
    
    def _update_position(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float
    ) -> None:
        """
        Pozisyon bilgisini günceller.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            price: İşlem fiyatı
        """
        try:
            current_time = datetime.now()
            
            if side == "BUY":
                if symbol not in self.positions:
                    # Yeni pozisyon
                    self.positions[symbol] = {
                        "symbol": symbol,
                        "quantity": quantity,
                        "entry_price": price,
                        "entry_time": current_time.isoformat(),
                        "last_update": current_time.isoformat()
                    }
                else:
                    # Mevcut pozisyonu güncelle
                    current_qty = self.positions[symbol]["quantity"]
                    current_price = self.positions[symbol]["entry_price"]
                    
                    # Ortalama giriş fiyatını hesapla
                    total_cost = (current_qty * current_price) + (quantity * price)
                    new_quantity = current_qty + quantity
                    new_price = total_cost / new_quantity
                    
                    self.positions[symbol].update({
                        "quantity": new_quantity,
                        "entry_price": new_price,
                        "last_update": current_time.isoformat()
                    })
            
            elif side == "SELL":
                if symbol in self.positions:
                    current_qty = self.positions[symbol]["quantity"]
                    
                    if quantity >= current_qty:
                        # Pozisyonu tamamen kapat
                        self.risk_manager.position_closed(symbol)
                        del self.positions[symbol]
                        logger.info(f"{symbol} pozisyonu tamamen kapatıldı")
                    else:
                        # Pozisyonu kısmen kapat
                        self.positions[symbol].update({
                            "quantity": current_qty - quantity,
                            "last_update": current_time.isoformat()
                        })
                        logger.info(f"{symbol} pozisyonu kısmen kapatıldı. Kalan: {current_qty - quantity}")
            
        except Exception as e:
            logger.error(f"Pozisyon güncellenirken hata: {e}")
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Açık pozisyonları döndürür.
        
        Returns:
            Dict: Açık pozisyonlar
        """
        return self.positions
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Emir geçmişini döndürür.
        
        Returns:
            List: Emir geçmişi
        """
        return self.orders
    
    def sync_positions_with_exchange(self) -> None:
        """
        Sistem pozisyonlarını borsa verileriyle senkronize eder.
        """
        try:
            account = self.client.get_account()
            balances = account.get("balances", [])
            
            # Açık pozisyonları kontrol et
            for symbol, position in list(self.positions.items()):
                # Sembolden baz varlığı çıkar (örn. BTCUSDT -> BTC)
                base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
                
                # Bakiyeyi bul
                for balance in balances:
                    if balance["asset"] == base_asset:
                        free_amount = float(balance["free"])
                        locked_amount = float(balance["locked"])
                        total_amount = free_amount + locked_amount
                        
                        if total_amount < 0.00001:  # Önemsiz miktar
                            # Pozisyonu kaldır
                            del self.positions[symbol]
                        else:
                            # Pozisyonu güncelle
                            self.positions[symbol]["quantity"] = total_amount
                        
                        break
            
            logger.info("Pozisyonlar borsa verileriyle senkronize edildi")
            
        except Exception as e:
            logger.error(f"Pozisyonlar senkronize edilirken hata: {e}") 
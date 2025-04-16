"""
Binance WebSocket client implementation for real-time price updates.
"""
import json
import threading
from typing import Dict, Callable
import websocket
from loguru import logger

class BinanceWebSocket:
    def __init__(self):
        """
        Binance WebSocket client'ı başlatır.
        """
        self.ws = None
        self.subscriptions = {}
        self.callbacks = {}
        self.thread = None
        self.is_running = False
        self.base_url = "wss://stream.binance.com:9443/ws"
        
    def _on_message(self, ws, message):
        """
        WebSocket mesajlarını işler.
        
        Args:
            ws: WebSocket bağlantısı
            message: Gelen mesaj
        """
        try:
            data = json.loads(message)
            symbol = data.get('s')
            if symbol in self.callbacks:
                price = float(data.get('p', 0))
                self.callbacks[symbol](price)
                logger.debug(f"{symbol} için fiyat güncellendi: {price}")
        except Exception as e:
            logger.error(f"WebSocket mesajı işlenirken hata oluştu: {e}")
    
    def _on_error(self, ws, error):
        """
        WebSocket hatalarını işler.
        
        Args:
            ws: WebSocket bağlantısı
            error: Hata mesajı
        """
        logger.error(f"WebSocket hatası: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket bağlantısı kapandığında çağrılır.
        
        Args:
            ws: WebSocket bağlantısı
            close_status_code: Kapanış durum kodu
            close_msg: Kapanış mesajı
        """
        logger.info("WebSocket bağlantısı kapandı")
        self.is_running = False
    
    def _on_open(self, ws):
        """
        WebSocket bağlantısı açıldığında çağrılır.
        
        Args:
            ws: WebSocket bağlantısı
        """
        logger.info("WebSocket bağlantısı açıldı")
        # Mevcut abonelikleri yeniden oluştur
        for symbol in self.subscriptions:
            self._subscribe(symbol)
    
    def _subscribe(self, symbol: str):
        """
        Belirli bir sembol için fiyat güncellemelerine abone olur.
        
        Args:
            symbol: Trading sembolü (örn. "BTCUSDT")
        """
        if self.ws and self.ws.sock and self.ws.sock.connected:
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@trade"],
                "id": 1
            }
            self.ws.send(json.dumps(subscribe_message))
            logger.info(f"{symbol} için fiyat güncellemelerine abone olundu")
    
    def _unsubscribe(self, symbol: str):
        """
        Belirli bir sembol için fiyat güncellemelerinden abonelikten çıkar.
        
        Args:
            symbol: Trading sembolü (örn. "BTCUSDT")
        """
        if self.ws and self.ws.sock and self.ws.sock.connected:
            unsubscribe_message = {
                "method": "UNSUBSCRIBE",
                "params": [f"{symbol.lower()}@trade"],
                "id": 1
            }
            self.ws.send(json.dumps(unsubscribe_message))
            logger.info(f"{symbol} için fiyat güncellemelerinden abonelikten çıkıldı")
    
    def start(self):
        """
        WebSocket bağlantısını başlatır.
        """
        if not self.is_running:
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                self.base_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()
            self.is_running = True
            logger.info("WebSocket client başlatıldı")
    
    def stop(self):
        """
        WebSocket bağlantısını durdurur.
        """
        if self.is_running and self.ws:
            self.ws.close()
            self.is_running = False
            logger.info("WebSocket client durduruldu")
    
    def subscribe_to_price_updates(self, symbol: str, callback: Callable[[float], None]):
        """
        Belirli bir sembol için fiyat güncellemelerine abone olur.
        
        Args:
            symbol: Trading sembolü (örn. "BTCUSDT")
            callback: Fiyat güncellendiğinde çağrılacak fonksiyon
        """
        if not self.is_running:
            self.start()
        
        self.subscriptions[symbol] = True
        self.callbacks[symbol] = callback
        self._subscribe(symbol)
    
    def unsubscribe_from_price_updates(self, symbol: str):
        """
        Belirli bir sembol için fiyat güncellemelerinden abonelikten çıkar.
        
        Args:
            symbol: Trading sembolü (örn. "BTCUSDT")
        """
        if symbol in self.subscriptions:
            self._unsubscribe(symbol)
            del self.subscriptions[symbol]
            del self.callbacks[symbol]
            logger.info(f"{symbol} için fiyat güncellemelerinden abonelikten çıkıldı") 
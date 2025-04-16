"""
WebSocket client for real-time price updates.
"""
import json
import threading
import time
from typing import Dict, Callable, Optional
import websocket
from loguru import logger

class BinanceWebSocket:
    def __init__(self, testnet: bool = False):
        """
        Binance WebSocket client'ı başlatır.
        
        Args:
            testnet: Testnet kullanılıp kullanılmayacağı (varsayılan: False)
        """
        self.testnet = testnet
        self.ws = None
        self.thread = None
        self.running = False
        self.callbacks = {}
        self.reconnect_delay = 5  # saniye
        self.max_reconnect_attempts = 5
        
        # WebSocket URL'ini ayarla
        if testnet:
            self.ws_url = "wss://testnet.binance.vision/ws"
            self.stream_url = "wss://testnet.binance.vision/stream"
        else:
            self.ws_url = "wss://stream.binance.com:9443/ws"
            self.stream_url = "wss://stream.binance.com:9443/stream"
    
    def _on_message(self, ws, message):
        """
        WebSocket mesajlarını işler.
        
        Args:
            ws: WebSocket bağlantısı
            message: Gelen mesaj
        """
        try:
            data = json.loads(message)
            
            # Stream mesajlarını işle
            if 'stream' in data:
                stream_data = data['data']
                stream_name = data['stream']
                
                if stream_name in self.callbacks:
                    self.callbacks[stream_name](stream_data)
            
            # Tekil mesajları işle
            elif 'e' in data:
                event_type = data['e']
                if event_type in self.callbacks:
                    self.callbacks[event_type](data)
                    
        except Exception as e:
            logger.error(f"WebSocket mesajı işlenirken hata: {e}")
    
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
            close_status_code: Kapanış kodu
            close_msg: Kapanış mesajı
        """
        logger.warning(f"WebSocket bağlantısı kapandı: {close_status_code} - {close_msg}")
        
        # Yeniden bağlanmayı dene
        if self.running:
            self.reconnect()
    
    def _on_open(self, ws):
        """
        WebSocket bağlantısı açıldığında çağrılır.
        
        Args:
            ws: WebSocket bağlantısı
        """
        logger.info("WebSocket bağlantısı açıldı")
    
    def reconnect(self):
        """
        WebSocket bağlantısını yeniden kurar.
        """
        if self.ws:
            self.ws.close()
        
        time.sleep(self.reconnect_delay)
        self.connect()
    
    def connect(self):
        """
        WebSocket bağlantısını başlatır.
        """
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        
        self.running = True
    
    def subscribe(self, stream: str, callback: Callable):
        """
        Belirli bir stream'e abone olur.
        
        Args:
            stream: Stream adı (örn. "btcusdt@trade")
            callback: Stream'den veri geldiğinde çağrılacak fonksiyon
        """
        if not self.running:
            self.connect()
        
        # Stream URL'ini oluştur
        stream_url = f"{self.stream_url}?streams={stream}"
        
        # Callback'i kaydet
        self.callbacks[stream] = callback
        
        # Stream'e abone ol
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream],
            "id": int(time.time() * 1000)
        }
        
        self.ws.send(json.dumps(subscribe_message))
        logger.info(f"{stream} stream'ine abone olundu")
    
    def unsubscribe(self, stream: str):
        """
        Belirli bir stream'den aboneliği kaldırır.
        
        Args:
            stream: Stream adı
        """
        if stream in self.callbacks:
            unsubscribe_message = {
                "method": "UNSUBSCRIBE",
                "params": [stream],
                "id": int(time.time() * 1000)
            }
            
            self.ws.send(json.dumps(unsubscribe_message))
            del self.callbacks[stream]
            logger.info(f"{stream} stream'inden abonelik kaldırıldı")
    
    def close(self):
        """
        WebSocket bağlantısını kapatır.
        """
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join()
        logger.info("WebSocket bağlantısı kapatıldı") 
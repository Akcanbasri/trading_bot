import os
from datetime import datetime
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from loguru import logger

class TelegramNotifier:
    def __init__(self):
        """Initialize TelegramNotifier with configuration from environment variables."""
        load_dotenv()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('ENABLE_TELEGRAM_NOTIFICATIONS', 'false').lower() == 'true'
        
        if not self.enabled:
            logger.info("Telegram notifications are disabled")
            return
            
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not found in environment variables")
            return
            
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
    def _send_message(self, message: str) -> bool:
        """Send a message to Telegram with error handling."""
        if not self.enabled:
            return False
            
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
            
    def notify_trade_open(self, symbol: str, trade_type: str, price: float, 
                         quantity: float, order_id: Optional[str] = None,
                         additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification when a trade is opened.
        
        Args:
            symbol: Trading pair symbol (e.g., 'DOGEUSDT')
            trade_type: Type of trade ('LONG' or 'SHORT')
            price: Entry price
            quantity: Trade quantity
            order_id: Optional order ID
            additional_info: Optional dictionary with additional trade information
        """
        message = (
            f"🔵 <b>Yeni İşlem Açıldı</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"📈 İşlem Tipi: {trade_type}\n"
            f"💰 Giriş Fiyatı: {price:.8f}\n"
            f"📊 Miktar: {quantity:.8f}\n"
        )
        
        if order_id:
            message += f"🆔 Sipariş ID: {order_id}\n"
            
        if additional_info:
            message += "\n📝 Ek Bilgiler:\n"
            for key, value in additional_info.items():
                message += f"• {key}: {value}\n"
            
        return self._send_message(message)
        
    def notify_trade_close(self, symbol: str, trade_type: str, entry_price: float,
                          exit_price: float, quantity: float, pnl: float,
                          pnl_percentage: float, order_id: Optional[str] = None,
                          additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification when a trade is closed.
        
        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('LONG' or 'SHORT')
            entry_price: Entry price
            exit_price: Exit price
            quantity: Trade quantity
            pnl: Profit/Loss in USDT
            pnl_percentage: Profit/Loss percentage
            order_id: Optional order ID
            additional_info: Optional dictionary with additional trade information
        """
        emoji = "🟢" if pnl > 0 else "🔴"
        message = (
            f"{emoji} <b>İşlem Kapatıldı</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"📉 İşlem Tipi: {trade_type}\n"
            f"💰 Giriş Fiyatı: {entry_price:.8f}\n"
            f"💰 Çıkış Fiyatı: {exit_price:.8f}\n"
            f"📊 Miktar: {quantity:.8f}\n"
            f"💵 Kar/Zarar: {pnl:.2f} USDT ({pnl_percentage:.2f}%)\n"
        )
        
        if order_id:
            message += f"🆔 Sipariş ID: {order_id}\n"
            
        if additional_info:
            message += "\n📝 Ek Bilgiler:\n"
            for key, value in additional_info.items():
                message += f"• {key}: {value}\n"
            
        return self._send_message(message)
        
    def notify_error(self, error_message: str, context: Optional[str] = None,
                    additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification when an error occurs.
        
        Args:
            error_message: Error message
            context: Optional context where the error occurred
            additional_info: Optional dictionary with additional error information
        """
        message = (
            f"⚠️ <b>Hata Bildirimi</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"❌ Hata: {error_message}\n"
        )
        
        if context:
            message += f"📝 Bağlam: {context}\n"
            
        if additional_info:
            message += "\n📝 Ek Bilgiler:\n"
            for key, value in additional_info.items():
                message += f"• {key}: {value}\n"
            
        return self._send_message(message) 
"""
Telegram notification service for the trading bot.
"""
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Telegram notification service for sending trading alerts.
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize the Telegram notifier.
        
        Args:
            bot_token: Telegram bot API token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Test connection on initialization
        if self.test_connection():
            logger.info("Telegram bağlantısı başarılı")
        else:
            logger.error("Telegram bağlantısı başarısız!")
    
    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection by sending a test message.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            response.raise_for_status()
            
            # Send a test message
            test_message = "🤖 Trading Bot başlatıldı!\n\nBağlantı testi başarılı."
            return self.send_message(test_message)
            
        except Exception as e:
            logger.error(f"Telegram bağlantı testi başarısız: {str(e)}")
            return False
    
    def send_message(self, message: str) -> bool:
        """
        Send a message via Telegram.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=data)
            response.raise_for_status()
            
            logger.info(f"Telegram mesajı gönderildi: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Telegram mesajı gönderilemedi: {str(e)}")
            logger.error(f"Hata detayı: Bot Token: {self.bot_token}, Chat ID: {self.chat_id}")
            return False
    
    def send_trade_notification(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        profit_loss: Optional[float] = None
    ) -> bool:
        """
        Send a trade notification.
        
        Args:
            symbol: Trading symbol (e.g., "DOGEUSDT")
            side: Trade side ("LONG" or "SHORT")
            quantity: Trade quantity
            price: Trade price
            profit_loss: Profit/loss amount (optional)
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        emoji = "🟢" if side == "LONG" else "🔴"
        message = (
            f"{emoji} <b>Yeni İşlem</b>\n\n"
            f"Sembol: {symbol}\n"
            f"Yön: {side}\n"
            f"Miktar: {quantity}\n"
            f"Fiyat: {price}"
        )
        
        if profit_loss is not None:
            pl_emoji = "📈" if profit_loss > 0 else "📉"
            message += f"\nKar/Zarar: {pl_emoji} {profit_loss:.2f} USDT"
        
        return self.send_message(message) 
"""
Telegram notification module for sending alerts and updates.
"""

import os
import logging
import requests
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """Abstract base class for notifiers."""

    @abstractmethod
    def send_message(self, message: str) -> bool:
        """Send a message through the notification channel."""
        pass


class TelegramNotifier(Notifier):
    """Telegram notification implementation."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_message(self, message: str) -> bool:
        """
        Send a message to Telegram.

        Args:
            message: Message to send

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}

            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()

            logger.debug(f"Telegram message sent successfully: {message[:100]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False

    def send_trade_notification(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_id: Optional[str] = None,
        leverage: Optional[int] = None,
        pnl: Optional[float] = None,
        is_open: bool = True,
    ) -> bool:
        """
        Send a formatted trade notification.

        Args:
            symbol: Trading pair symbol
            side: Trade side (BUY/SELL)
            quantity: Trade quantity
            price: Trade price (optional)
            order_id: Order ID (optional)
            leverage: Leverage used (optional)
            pnl: Profit/Loss (optional)
            is_open: True if opening position, False if closing

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Determine position type and status
            position_type = "LONG" if side == "BUY" else "SHORT"
            position_status = "OPENED" if is_open else "CLOSED"
            emoji = "🟢" if side == "BUY" else "🔴"

            # Format the message
            message = f"🔔 <b>Trade Notification</b>\n\n"
            message += f"Position: {emoji} {position_type} {position_status}\n"
            message += f"Symbol: {symbol}\n"
            message += f"Quantity: {quantity}\n"

            if price:
                message += f"Price: {price}\n"
            if leverage:
                message += f"Leverage: {leverage}x\n"
            if order_id:
                message += f"Order ID: {order_id}\n"
            if pnl is not None:
                emoji = "✅" if pnl > 0 else "❌"
                message += f"PnL: {emoji} {pnl:.2f} USDT\n"

            return self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send trade notification: {str(e)}")
            return False

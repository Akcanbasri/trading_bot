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
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = (
            os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "false").lower() == "true"
        )

        if not self.enabled:
            logger.info("Telegram notifications are disabled")
            return

        if not self.token or not self.chat_id:
            logger.warning(
                "Telegram bot token or chat ID not found in environment variables"
            )
            return

        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def _send_message(self, message: str) -> bool:
        """Send a message to Telegram with error handling."""
        if not self.enabled:
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False

    def notify_trade_open(
        self,
        symbol: str,
        trade_type: str,
        price: float,
        quantity: float,
        order_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
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

    def notify_trade_close(
        self,
        symbol: str,
        trade_type: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_percentage: float,
        order_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
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

    def notify_error(
        self,
        error_message: str,
        context: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
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

    def notify_indicator_signal(
        self, symbol: str, signal_type: str, indicator_values: Dict[str, Any]
    ) -> bool:
        """
        Send notification when an indicator signal is detected.

        Args:
            symbol: Trading pair symbol
            signal_type: Type of signal ('LONG' or 'SHORT')
            indicator_values: Dictionary with indicator values
        """
        emoji = "📈" if signal_type == "LONG" else "📉"
        message = (
            f"{emoji} <b>{signal_type} Sinyali Tespit Edildi</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
        )

        # Add indicator values
        message += "\n📊 Gösterge Değerleri:\n"
        for key, value in indicator_values.items():
            message += f"• {key}: {value}\n"

        return self._send_message(message)

    def notify_leverage_calculation(
        self,
        symbol: str,
        leverage: int,
        notional_size: float,
        margin_required: float,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Send notification about leverage calculation.

        Args:
            symbol: Trading pair symbol
            leverage: Calculated leverage
            notional_size: Notional size in USDT
            margin_required: Required margin in USDT
            reason: Optional reason for the calculation
        """
        message = (
            f"🔧 <b>Kaldıraç Ayarlandı</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"📊 Kaldıraç: {leverage}x\n"
            f"💰 Nominal Değer: {notional_size:.2f} USDT\n"
            f"💵 Gerekli Teminat: {margin_required:.2f} USDT\n"
        )

        if reason:
            message += f"📝 Neden: {reason}\n"

        return self._send_message(message)

    def notify_leverage_constraint(
        self, symbol: str, reason: str, details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification when a trade is skipped due to leverage constraints.

        Args:
            symbol: Trading pair symbol
            reason: Reason for the constraint
            details: Optional dictionary with additional details
        """
        message = (
            f"⚠️ <b>İşlem Atlanıldı (Kaldıraç)</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"❌ Neden: {reason}\n"
        )

        if details:
            message += "\n📝 Detaylar:\n"
            for key, value in details.items():
                message += f"• {key}: {value}\n"

        return self._send_message(message)

    def notify_scaled_entry(
        self,
        symbol: str,
        trade_type: str,
        tier: int,
        entry_price: float,
        position_size: float,
        total_position_size: float,
        leverage: int,
        stop_loss: float,
    ) -> bool:
        """
        Send notification for a scaled entry.

        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('LONG' or 'SHORT')
            tier: Entry tier (1, 2, or 3)
            entry_price: Entry price
            position_size: Position size for this entry
            total_position_size: Total position size after this entry
            leverage: Leverage used
            stop_loss: Stop loss price
        """
        emoji = "✅" if tier == 1 else "➕"
        tier_text = "Tier 1" if tier == 1 else f"Tier {tier} Eklendi"

        message = (
            f"{emoji} <b>{trade_type} {tier_text}</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"💰 Giriş Fiyatı: {entry_price:.8f}\n"
            f"📊 Miktar: {position_size:.8f}\n"
            f"📈 Toplam Miktar: {total_position_size:.8f}\n"
            f"📊 Kaldıraç: {leverage}x\n"
            f"🛑 Stop-Loss: {stop_loss:.8f}\n"
        )

        return self._send_message(message)

    def notify_scaled_exit(
        self,
        symbol: str,
        trade_type: str,
        tier: int,
        exit_price: float,
        closed_size: float,
        pnl: float,
        pnl_percentage: float,
    ) -> bool:
        """
        Send notification for a scaled exit.

        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('LONG' or 'SHORT')
            tier: Exit tier (1, 2, or 3)
            exit_price: Exit price
            closed_size: Size of the position closed
            pnl: Profit/Loss in USDT
            pnl_percentage: Profit/Loss percentage
        """
        emoji = "💰"
        message = (
            f"{emoji} <b>{trade_type} TP Scaled Out [Tier {tier}]</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"💰 Çıkış Fiyatı: {exit_price:.8f}\n"
            f"📊 Kapatılan Miktar: {closed_size:.8f}\n"
            f"�� Kar/Zarar: {pnl:.2f} USDT ({pnl_percentage:.2f}%)\n"
        )

        return self._send_message(message)

    def notify_stop_loss_hit(
        self,
        symbol: str,
        trade_type: str,
        exit_price: float,
        closed_size: float,
        pnl: float,
        pnl_percentage: float,
    ) -> bool:
        """
        Send notification when stop-loss is hit.

        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('LONG' or 'SHORT')
            exit_price: Exit price
            closed_size: Size of the position closed
            pnl: Profit/Loss in USDT
            pnl_percentage: Profit/Loss percentage
        """
        message = (
            f"🛑 <b>{trade_type} Stop-Loss Hit</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"💰 Çıkış Fiyatı: {exit_price:.8f}\n"
            f"📊 Kapatılan Miktar: {closed_size:.8f}\n"
            f"💵 Kar/Zarar: {pnl:.2f} USDT ({pnl_percentage:.2f}%)\n"
        )

        return self._send_message(message)

    def notify_final_exit(
        self,
        symbol: str,
        trade_type: str,
        exit_price: float,
        closed_size: float,
        pnl: float,
        pnl_percentage: float,
        reason: str,
    ) -> bool:
        """
        Send notification for a final exit due to a strategy signal.

        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('LONG' or 'SHORT')
            exit_price: Exit price
            closed_size: Size of the position closed
            pnl: Profit/Loss in USDT
            pnl_percentage: Profit/Loss percentage
            reason: Reason for the exit
        """
        message = (
            f"🚪 <b>{trade_type} Final Exit (Signal)</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"💰 Çıkış Fiyatı: {exit_price:.8f}\n"
            f"📊 Kapatılan Miktar: {closed_size:.8f}\n"
            f"💵 Kar/Zarar: {pnl:.2f} USDT ({pnl_percentage:.2f}%)\n"
            f"📝 Neden: {reason}\n"
        )

        return self._send_message(message)

    def notify_stop_loss_adjusted(
        self, symbol: str, new_stop_loss: float, reason: str
    ) -> bool:
        """
        Send notification when stop-loss is adjusted.

        Args:
            symbol: Trading pair symbol
            new_stop_loss: New stop-loss price
            reason: Reason for the adjustment
        """
        message = (
            f"🛡️ <b>SL Adjusted</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💱 Sembol: {symbol}\n"
            f"🛑 Yeni SL Fiyatı: {new_stop_loss:.8f}\n"
            f"📝 Neden: {reason}\n"
        )

        return self._send_message(message)

    def notify_bot_started(self) -> bool:
        """
        Send notification when the bot is started.

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        message = (
            f"🚀 <b>Trading Bot Başlatıldı</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        return self._send_message(message)

    def notify_bot_stopped(self) -> bool:
        """
        Send notification when the bot is stopped.

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        message = (
            f"🛑 <b>Trading Bot Durduruldu</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        return self._send_message(message)

    def notify_bot_status(
        self,
        balance: float,
        open_position: bool,
        position_symbol: Optional[str] = None,
        position_side: Optional[str] = None,
    ) -> bool:
        """
        Send periodic status update.

        Args:
            balance: Current account balance
            open_position: Whether there is an open position
            position_symbol: Symbol of the open position, if any
            position_side: Side of the open position (LONG/SHORT), if any
        """
        message = (
            f"ℹ️ <b>Bot Status Update</b>\n\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💰 Bakiye: {balance:.2f} USDT\n"
            f"📊 Açık Pozisyon: {'Evet' if open_position else 'Hayır'}\n"
        )

        if open_position and position_symbol and position_side:
            message += f"💱 Pozisyon: {position_symbol} ({position_side})\n"

        return self._send_message(message)

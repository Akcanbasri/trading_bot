"""
Order Manager sınıfı.

Bu modül, emir yönetimi için gerekli fonksiyonları sağlar.
"""

import os
import time
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from loguru import logger
from src.api.client import BinanceClient
from src.utils.log_throttler import LogThrottler


class OrderManager:
    """
    Emir yönetimi sınıfı.

    Emir oluşturma, iptal etme ve takip etme işlemlerini yönetir.
    """

    def __init__(self, client: BinanceClient):
        """
        Order Manager sınıfını başlatır.

        Args:
            client: Binance API istemcisi
        """
        self.client = client
        self.symbol = os.getenv("TRADING_SYMBOL", "DOGEUSDT")
        self.leverage = int(os.getenv("LEVERAGE", "20"))
        self.risk_amount = float(os.getenv("RISK_AMOUNT", "10"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))
        self.take_profit_percent = float(os.getenv("TAKE_PROFIT_PERCENT", "4.0"))
        self.trailing_stop_callback_rate = float(
            os.getenv("TRAILING_STOP_CALLBACK_RATE", "1.0")
        )

        # Initialize log throttler with default 60-second interval
        self.log_throttler = LogThrottler(default_interval=60.0)

        # Set custom intervals for specific log types
        self.log_throttler.set_interval(
            "order_check", 30.0
        )  # Order checks every 30 seconds
        self.log_throttler.set_interval(
            "position_check", 60.0
        )  # Position checks every 60 seconds
        self.log_throttler.set_interval(
            "balance_check", 300.0
        )  # Balance checks every 5 minutes

        logger.info("Order Manager başlatıldı")

    def open_long_position(self, quantity: float) -> Dict[str, Any]:
        """
        Long pozisyon açar.

        Args:
            quantity: İşlem miktarı

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            # Kaldıraç oranını ayarla
            self.client.futures_change_leverage(
                symbol=self.symbol, leverage=self.leverage
            )

            # Long pozisyon aç
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side="BUY",
                order_type="MARKET",
                quantity=quantity,
                reduce_only=False,
            )

            # Stop Loss ve Take Profit emirlerini oluştur
            entry_price = float(order["avgPrice"])
            stop_loss_price = entry_price * (1 - self.stop_loss_percent / 100)
            take_profit_price = entry_price * (1 + self.take_profit_percent / 100)

            # Stop Loss emri oluştur
            stop_loss_order = self.client.create_stop_loss_order(
                symbol=self.symbol,
                side="SELL",
                quantity=quantity,
                stop_price=stop_loss_price,
            )

            # Take Profit emri oluştur
            take_profit_order = self.client.create_take_profit_order(
                symbol=self.symbol,
                side="SELL",
                quantity=quantity,
                take_profit_price=take_profit_price,
            )

            # Use throttled logging for position details
            self.log_throttler.log(
                f"position_{self.symbol}",
                f"Long pozisyon açıldı: {order}\n"
                f"Stop Loss: {stop_loss_order}\n"
                f"Take Profit: {take_profit_order}",
                level="info",
            )

            return {
                "entry_order": order,
                "stop_loss_order": stop_loss_order,
                "take_profit_order": take_profit_order,
            }
        except Exception as e:
            logger.error(f"Long pozisyon açılırken hata oluştu: {e}")
            raise

    def open_short_position(self, quantity: float) -> Dict[str, Any]:
        """
        Short pozisyon açar.

        Args:
            quantity: İşlem miktarı

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            # Kaldıraç oranını ayarla
            self.client.futures_change_leverage(
                symbol=self.symbol, leverage=self.leverage
            )

            # Short pozisyon aç
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side="SELL",
                order_type="MARKET",
                quantity=quantity,
                reduce_only=False,
            )

            # Stop Loss ve Take Profit emirlerini oluştur
            entry_price = float(order["avgPrice"])
            stop_loss_price = entry_price * (1 + self.stop_loss_percent / 100)
            take_profit_price = entry_price * (1 - self.take_profit_percent / 100)

            # Stop Loss emri oluştur
            stop_loss_order = self.client.create_stop_loss_order(
                symbol=self.symbol,
                side="BUY",
                quantity=quantity,
                stop_price=stop_loss_price,
            )

            # Take Profit emri oluştur
            take_profit_order = self.client.create_take_profit_order(
                symbol=self.symbol,
                side="BUY",
                quantity=quantity,
                take_profit_price=take_profit_price,
            )

            # Use throttled logging for position details
            self.log_throttler.log(
                f"position_{self.symbol}",
                f"Short pozisyon açıldı: {order}\n"
                f"Stop Loss: {stop_loss_order}\n"
                f"Take Profit: {take_profit_order}",
                level="info",
            )

            return {
                "entry_order": order,
                "stop_loss_order": stop_loss_order,
                "take_profit_order": take_profit_order,
            }
        except Exception as e:
            logger.error(f"Short pozisyon açılırken hata oluştu: {e}")
            raise

    def close_position(self) -> Dict[str, Any]:
        """
        Mevcut pozisyonu kapatır.

        Returns:
            Dict[str, Any]: İşlem sonucu
        """
        try:
            # Tüm açık emirleri iptal et
            self.client.cancel_all_orders(self.symbol)

            # Pozisyon bilgilerini al
            position = self.client.get_futures_position(self.symbol)
            if not position:
                # Use throttled logging for position checks
                self.log_throttler.log(
                    f"position_{self.symbol}",
                    f"{self.symbol} için açık pozisyon bulunamadı",
                    level="info",
                )
                return {}

            # Pozisyon miktarını al
            quantity = abs(float(position["positionAmt"]))
            if quantity == 0:
                # Use throttled logging for position checks
                self.log_throttler.log(
                    f"position_{self.symbol}",
                    f"{self.symbol} için pozisyon miktarı 0",
                    level="info",
                )
                return {}

            # Pozisyon yönünü belirle
            side = "SELL" if float(position["positionAmt"]) > 0 else "BUY"

            # Pozisyonu kapat
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                order_type="MARKET",
                quantity=quantity,
                reduce_only=True,
            )

            # Use throttled logging for position details
            self.log_throttler.log(
                f"position_{self.symbol}", f"Pozisyon kapatıldı: {order}", level="info"
            )

            return order
        except Exception as e:
            logger.error(f"Pozisyon kapatılırken hata oluştu: {e}")
            raise

    def update_trailing_stop(
        self, quantity: float, callback_rate: float
    ) -> Dict[str, Any]:
        """
        Trailing Stop emrini günceller.

        Args:
            quantity: İşlem miktarı
            callback_rate: Geri çağırma oranı

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            # Pozisyon bilgilerini al
            position = self.client.get_futures_position(self.symbol)
            if not position:
                # Use throttled logging for position checks
                self.log_throttler.log(
                    f"position_{self.symbol}",
                    f"{self.symbol} için açık pozisyon bulunamadı",
                    level="info",
                )
                return {}

            # Pozisyon yönünü belirle
            side = "SELL" if float(position["positionAmt"]) > 0 else "BUY"

            # Trailing Stop emri oluştur
            order = self.client.create_trailing_stop_order(
                symbol=self.symbol,
                side=side,
                quantity=quantity,
                callback_rate=callback_rate,
            )

            # Use throttled logging for order details
            self.log_throttler.log(
                f"order_{self.symbol}",
                f"Trailing Stop emri güncellendi: {order}",
                level="info",
            )

            return order
        except Exception as e:
            logger.error(f"Trailing Stop emri güncellenirken hata oluştu: {e}")
            raise

    def get_position_info(self) -> Dict[str, Any]:
        """
        Mevcut pozisyon bilgilerini döndürür.

        Returns:
            Dict[str, Any]: Pozisyon bilgileri
        """
        try:
            position = self.client.get_futures_position(self.symbol)
            if not position:
                # Use throttled logging for position checks
                self.log_throttler.log(
                    f"position_{self.symbol}",
                    f"{self.symbol} için açık pozisyon bulunamadı",
                    level="info",
                )
                return {}

            # Use throttled logging for position details
            self.log_throttler.log(
                f"position_{self.symbol}",
                f"Pozisyon bilgileri: {position}",
                level="debug",
            )

            return position
        except Exception as e:
            logger.error(f"Pozisyon bilgileri alınırken hata oluştu: {e}")
            raise

    def calculate_position_size(self) -> Optional[float]:
        """
        Risk bazlı pozisyon büyüklüğünü hesaplar.

        Returns:
            Optional[float]: Pozisyon büyüklüğü veya None (hata durumunda)
        """
        try:
            position_size = self.client.calculate_position_size(
                symbol=self.symbol,
                risk_amount=self.risk_amount,
                stop_loss_percent=self.stop_loss_percent,
                leverage=self.leverage,
            )

            # Use throttled logging for position size calculations
            self.log_throttler.log(
                f"position_size_{self.symbol}",
                f"Risk bazlı pozisyon büyüklüğü hesaplandı: {position_size}",
                level="debug",
            )

            return position_size
        except Exception as e:
            logger.error(f"Pozisyon büyüklüğü hesaplanırken hata oluştu: {e}")
            return None

    def get_risk_metrics(
        self, position_size: float, entry_price: float
    ) -> Dict[str, float]:
        """
        Pozisyon risk metriklerini hesaplar.

        Args:
            position_size: Pozisyon büyüklüğü
            entry_price: Giriş fiyatı

        Returns:
            Dict[str, float]: Risk metrikleri
        """
        try:
            risk_metrics = self.client.get_futures_position_risk(
                symbol=self.symbol,
                position_size=position_size,
                entry_price=entry_price,
                leverage=self.leverage,
            )

            # Use throttled logging for risk metrics
            self.log_throttler.log(
                f"risk_metrics_{self.symbol}",
                f"Risk metrikleri hesaplandı: {risk_metrics}",
                level="debug",
            )

            return risk_metrics
        except Exception as e:
            logger.error(f"Risk metrikleri hesaplanırken hata oluştu: {e}")
            return {}

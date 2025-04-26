"""
Emir yönetimi modülü.

Bu modül, emirlerin oluşturulması, yönetilmesi ve izlenmesi için gerekli fonksiyonları sağlar.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, ROUND_DOWN
from loguru import logger

from src.api.client import BinanceClient
from src.utils.notifier import Notifier


class OrderManager:
    """
    Emir yönetimi sınıfı.

    Emirlerin oluşturulması, yönetilmesi ve izlenmesi için gerekli metodları sağlar.
    """

    def __init__(self, client: BinanceClient, notifier: Optional[Notifier] = None):
        """
        Emir yönetimi sınıfını başlatır.

        Args:
            client: Binance API istemcisi
            notifier: Bildirim gönderici (opsiyonel)
        """
        self.client = client
        self.notifier = notifier

        # .env dosyasından emir parametrelerini oku
        self.default_leverage = int(os.getenv("DEFAULT_LEVERAGE", "5"))
        self.default_risk_amount = float(os.getenv("DEFAULT_RISK_AMOUNT", "100"))
        self.default_stop_loss_percent = float(
            os.getenv("DEFAULT_STOP_LOSS_PERCENT", "2.0")
        )
        self.default_take_profit_percent = float(
            os.getenv("DEFAULT_TAKE_PROFIT_PERCENT", "4.0")
        )
        self.use_trailing_stop = (
            os.getenv("USE_TRAILING_STOP", "false").lower() == "true"
        )
        self.trailing_stop_callback_rate = float(
            os.getenv("TRAILING_STOP_CALLBACK_RATE", "1.0")
        )
        self.use_oco = os.getenv("USE_OCO", "false").lower() == "true"
        self.min_notional = float(os.getenv("MIN_NOTIONAL", "5.0"))

        # Emir tipleri
        self.order_types = {
            "SIMPLE": os.getenv("ORDER_TYPE_SIMPLE", "true").lower() == "true",
            "SL_TP": os.getenv("ORDER_TYPE_SL_TP", "true").lower() == "true",
            "OCO": os.getenv("ORDER_TYPE_OCO", "true").lower() == "true",
            "TRAILING_STOP": os.getenv("ORDER_TYPE_TRAILING_STOP", "true").lower()
            == "true",
            "RISK_MANAGEMENT": os.getenv("ORDER_TYPE_RISK_MANAGEMENT", "true").lower()
            == "true",
        }

        logger.info("Emir yönetimi sınıfı başlatıldı")
        logger.info(
            f"Varsayılan emir parametreleri: Kaldıraç={self.default_leverage}, "
            f"Risk={self.default_risk_amount}, SL={self.default_stop_loss_percent}, "
            f"TP={self.default_take_profit_percent}, Trailing Stop={self.use_trailing_stop}, "
            f"OCO={self.use_oco}"
        )

    def send_notification(self, message: str) -> None:
        """
        Bildirim gönderir.

        Args:
            message: Bildirim mesajı
        """
        if self.notifier:
            try:
                logger.debug(f"Bildirim gönderiliyor: {message}")
                self.notifier.send_message(message)
            except Exception as e:
                logger.error(f"Bildirim gönderilirken hata oluştu: {e}")

    def send_trade_notification(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_id: str,
        leverage: int,
        is_open: bool,
    ) -> None:
        """
        İşlem bildirimi gönderir.

        Args:
            symbol: Trading sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            order_id: Emir ID'si
            leverage: Kaldıraç oranı
            is_open: Pozisyon açılıyor mu (True) veya kapatılıyor mu (False)
        """
        if self.notifier:
            try:
                action = "açıldı" if is_open else "kapatıldı"
                message = f"🔔 {symbol} {side} {quantity}@{leverage}x pozisyonu {action} (Emir ID: {order_id})"
                logger.debug(f"İşlem bildirimi gönderiliyor: {message}")
                self.notifier.send_trade_notification(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_id=order_id,
                    leverage=leverage,
                    is_open=is_open,
                )
            except Exception as e:
                logger.error(f"İşlem bildirimi gönderilirken hata oluştu: {e}")

    def calculate_min_quantity(
        self, symbol: str, min_notional: float = 5.0
    ) -> Optional[float]:
        """
        Minimum miktarı hesaplar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            min_notional: Minimum nominal değer (varsayılan: 5.0)

        Returns:
            Optional[float]: Minimum miktar veya None (hata durumunda)
        """
        try:
            logger.debug(
                f"Calculating minimum quantity for {symbol} with min_notional={min_notional}"
            )
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                return None

            min_qty = min_notional / current_price

            # Round to the symbol's precision requirements
            precision = self.client.get_futures_quantity_precision(symbol)
            min_qty = float(
                Decimal(str(min_qty)).quantize(
                    Decimal("0." + "0" * precision), rounding=ROUND_DOWN
                )
            )
            logger.info(
                f"Calculated minimum quantity for {symbol}: {min_qty} at price {current_price} (precision: {precision})"
            )
            return min_qty
        except Exception as e:
            logger.error(f"Error calculating minimum quantity: {e}")
            return None

    def open_position(
        self, symbol: str, side: str, leverage: int, min_notional: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Yeni bir pozisyon açar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            leverage: Kaldıraç oranı
            min_notional: Minimum nominal değer (varsayılan: 5.0)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            logger.info(
                f"{symbol} için {side} pozisyonu açılıyor (kaldıraç: {leverage}x)"
            )
            self.send_notification(
                f"🚀 {symbol} için {side} pozisyonu açılıyor (kaldıraç: {leverage}x)"
            )

            # Get server time offset for spot API
            spot_offset = self.client.get_server_time()
            logger.info(f"Spot server time offset: {spot_offset}ms")

            # Get server time offset for futures API
            futures_offset = self.client.get_server_time(is_futures=True)
            logger.info(f"Futures server time offset: {futures_offset}ms")

            # Wait a second before proceeding
            time.sleep(1)

            # Kaldıracı ayarla
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.debug(f"{symbol} için kaldıraç {leverage}x olarak ayarlandı")

            # Calculate minimum quantity
            min_qty = self.calculate_min_quantity(symbol, min_notional)
            if not min_qty:
                raise ValueError(f"{symbol} için minimum miktar hesaplanamadı")

            # Place test order with exact precision
            order_qty = float(
                Decimal(str(min_qty * 1.1)).quantize(
                    Decimal(
                        "0." + "0" * self.client.get_futures_quantity_precision(symbol)
                    ),
                    rounding=ROUND_DOWN,
                )
            )

            logger.info(
                f"{symbol} için {side} emri oluşturuluyor (miktar: {order_qty})"
            )

            # Emri gönder
            order = self.client.futures_create_order(
                symbol=symbol, side=side, order_type="MARKET", quantity=order_qty
            )

            order_id = order.get("orderId")
            logger.info(f"{side} emri başarıyla oluşturuldu. Emir ID: {order_id}")

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=order_qty,
                order_id=str(order_id),
                leverage=leverage,
                is_open=True,
            )

            return order
        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {side} pozisyonu açılırken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def close_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Mevcut bir pozisyonu kapatır.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda veya pozisyon yoksa)
        """
        try:
            # Pozisyon bilgilerini al
            position = self.client.get_futures_position(symbol)
            if not position:
                logger.info(f"{symbol} için açık pozisyon bulunamadı")
                return None

            position_amt = float(position["positionAmt"])
            if position_amt == 0:
                logger.info(f"{symbol} için açık pozisyon bulunamadı")
                return None

            # Pozisyon yönünü belirle
            side = "SELL" if position_amt > 0 else "BUY"
            quantity = abs(position_amt)
            leverage = int(position["leverage"])

            logger.info(
                f"{symbol} için {side} pozisyonu kapatılıyor (miktar: {quantity})"
            )
            self.send_notification(
                f"🔚 {symbol} için {side} pozisyonu kapatılıyor (miktar: {quantity})"
            )

            # Emri gönder
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                order_type="MARKET",
                quantity=quantity,
                reduce_only=True,
            )

            order_id = order.get("orderId")
            logger.info(
                f"Pozisyon kapatma emri başarıyla oluşturuldu. Emir ID: {order_id}"
            )

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_id=str(order_id),
                leverage=leverage,
                is_open=False,
            )

            return order
        except Exception as e:
            error_msg = f"❌ {symbol} için pozisyon kapatılırken hata oluştu: {str(e)}"
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def open_position_with_trailing_stop(
        self,
        symbol: str,
        side: str,
        leverage: int,
        callback_rate: float,
        min_notional: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Trailing Stop ile yeni bir pozisyon açar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            leverage: Kaldıraç oranı
            callback_rate: Geri çağırma oranı (örn. 1.0 = %1)
            min_notional: Minimum nominal değer (varsayılan: 5.0)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            # Mevcut emirleri iptal et
            self.client.cancel_all_orders(symbol)

            # Kaldıracı ayarla
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

            # Minimum miktarı hesapla
            min_qty = self.client.calculate_min_quantity(symbol, min_notional)
            if not min_qty:
                raise ValueError(f"{symbol} için minimum miktar hesaplanamadı")

            # Emir miktarını hesapla (minimum miktarın %10 fazlası)
            order_qty = float(
                Decimal(str(min_qty * 1.1)).quantize(
                    Decimal(
                        "0." + "0" * self.client.get_futures_quantity_precision(symbol)
                    ),
                    rounding=ROUND_DOWN,
                )
            )

            # Mevcut fiyatı al
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            # Ana emri oluştur
            order = self.client.futures_create_order(
                symbol=symbol, side=side, order_type="MARKET", quantity=order_qty
            )

            # Trailing Stop emrini oluştur
            trailing_stop_order = self.client.create_trailing_stop_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                quantity=order_qty,
                callback_rate=callback_rate,
            )

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=order_qty,
                order_id=str(order.get("orderId")),
                leverage=leverage,
                is_open=True,
            )

            self.send_notification(
                f"🔔 {symbol} {side} pozisyonu açıldı (Trailing Stop):\n"
                f"Giriş: {current_price:.8f}\n"
                f"Trailing Stop: {callback_rate}%"
            )

            return {"entry_order": order, "trailing_stop_order": trailing_stop_order}

        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {side} pozisyonu açılırken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def open_position_with_risk_management(
        self,
        symbol: str,
        side: str,
        leverage: int,
        risk_amount: float,
        stop_loss_percent: float,
        take_profit_percent: Optional[float] = None,
        use_trailing_stop: bool = False,
        trailing_stop_callback_rate: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Risk yönetimi ile yeni bir pozisyon açar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            leverage: Kaldıraç oranı
            risk_amount: Risk edilecek miktar (USDT)
            stop_loss_percent: Stop Loss yüzdesi (örn. 2.0 = %2)
            take_profit_percent: Take Profit yüzdesi (opsiyonel)
            use_trailing_stop: Trailing Stop kullanılsın mı (varsayılan: False)
            trailing_stop_callback_rate: Trailing Stop geri çağırma oranı (opsiyonel)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            # Mevcut emirleri iptal et
            self.client.cancel_all_orders(symbol)

            # Kaldıracı ayarla
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

            # Risk bazlı pozisyon büyüklüğünü hesapla
            position_size = self.client.calculate_position_size(
                symbol=symbol,
                risk_amount=risk_amount,
                stop_loss_percent=stop_loss_percent,
                leverage=leverage,
            )
            if not position_size:
                raise ValueError(f"{symbol} için pozisyon büyüklüğü hesaplanamadı")

            # Mevcut fiyatı al
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            # Risk metriklerini hesapla
            risk_metrics = self.client.get_futures_position_risk(
                symbol=symbol,
                position_size=position_size,
                entry_price=current_price,
                leverage=leverage,
            )

            # Ana emri oluştur
            order = self.client.futures_create_order(
                symbol=symbol, side=side, order_type="MARKET", quantity=position_size
            )

            orders = {"entry_order": order}

            # Stop Loss emrini oluştur
            stop_loss_price = (
                current_price * (1 - stop_loss_percent / 100)
                if side == "BUY"
                else current_price * (1 + stop_loss_percent / 100)
            )
            stop_loss_order = self.client.create_stop_loss_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                quantity=position_size,
                stop_price=stop_loss_price,
            )
            orders["stop_loss_order"] = stop_loss_order

            # Take Profit veya Trailing Stop emrini oluştur
            if use_trailing_stop and trailing_stop_callback_rate:
                trailing_stop_order = self.client.create_trailing_stop_order(
                    symbol=symbol,
                    side="SELL" if side == "BUY" else "BUY",
                    quantity=position_size,
                    callback_rate=trailing_stop_callback_rate,
                )
                orders["trailing_stop_order"] = trailing_stop_order
            elif take_profit_percent:
                take_profit_price = (
                    current_price * (1 + take_profit_percent / 100)
                    if side == "BUY"
                    else current_price * (1 - take_profit_percent / 100)
                )
                take_profit_order = self.client.create_take_profit_order(
                    symbol=symbol,
                    side="SELL" if side == "BUY" else "BUY",
                    quantity=position_size,
                    take_profit_price=take_profit_price,
                )
                orders["take_profit_order"] = take_profit_order

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=position_size,
                order_id=str(order.get("orderId")),
                leverage=leverage,
                is_open=True,
            )

            # Risk metrikleri ile birlikte bildirim gönder
            notification = (
                f"🔔 {symbol} {side} pozisyonu açıldı (Risk Yönetimi):\n"
                f"Giriş: {current_price:.8f}\n"
                f"Stop Loss: {stop_loss_price:.8f} ({stop_loss_percent}%)\n"
            )

            if use_trailing_stop and trailing_stop_callback_rate:
                notification += f"Trailing Stop: {trailing_stop_callback_rate}%\n"
            elif take_profit_percent:
                take_profit_price = (
                    current_price * (1 + take_profit_percent / 100)
                    if side == "BUY"
                    else current_price * (1 - take_profit_percent / 100)
                )
                notification += (
                    f"Take Profit: {take_profit_price:.8f} ({take_profit_percent}%)\n"
                )

            notification += (
                f"Pozisyon Büyüklüğü: {position_size:.8f}\n"
                f"Risk Edilen: {risk_amount:.2f} USDT\n"
                f"Maksimum Kayıp: {risk_metrics['max_loss']:.2f} USDT\n"
                f"Beklenen Kâr: {risk_metrics['expected_profit']:.2f} USDT\n"
                f"Risk/Ödül Oranı: 1:{risk_metrics['risk_reward_ratio']:.1f}"
            )

            self.send_notification(notification)

            return orders

        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {side} pozisyonu açılırken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def execute_signal(
        self,
        symbol: str,
        signal: str,
        leverage: Optional[int] = None,
        stop_loss_percent: Optional[float] = None,
        take_profit_percent: Optional[float] = None,
        use_oco: Optional[bool] = None,
        trailing_stop_callback_rate: Optional[float] = None,
        risk_amount: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sinyal doğrultusunda işlem gerçekleştirir.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            signal: İşlem sinyali ("LONG", "SHORT" veya "HOLD")
            leverage: Kaldıraç oranı (varsayılan: .env'den alınır)
            stop_loss_percent: Stop Loss yüzdesi (varsayılan: .env'den alınır)
            take_profit_percent: Take Profit yüzdesi (varsayılan: .env'den alınır)
            use_oco: OCO emri kullanılsın mı (varsayılan: .env'den alınır)
            trailing_stop_callback_rate: Trailing Stop geri çağırma oranı (varsayılan: .env'den alınır)
            risk_amount: Risk edilecek miktar (USDT) (varsayılan: .env'den alınır)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            # Varsayılan değerleri kullan
            leverage = leverage or self.default_leverage
            stop_loss_percent = stop_loss_percent or self.default_stop_loss_percent
            take_profit_percent = (
                take_profit_percent or self.default_take_profit_percent
            )
            use_oco = use_oco if use_oco is not None else self.use_oco
            trailing_stop_callback_rate = (
                trailing_stop_callback_rate or self.trailing_stop_callback_rate
            )
            risk_amount = risk_amount or self.default_risk_amount

            # Mevcut pozisyonu kontrol et
            position = self.client.get_futures_position(symbol)
            has_position = position is not None and float(position["positionAmt"]) != 0

            # Sinyal doğrultusunda işlem yap
            if signal == "LONG":
                if has_position and float(position["positionAmt"]) < 0:
                    # SHORT pozisyonu kapat
                    logger.info(
                        f"{symbol} için SHORT pozisyonu kapatılıyor (LONG sinyali)"
                    )
                    self.close_position(symbol)
                    # LONG pozisyonu aç
                    logger.info(f"{symbol} için LONG pozisyonu açılıyor")

                    # Emir tipini belirle
                    if self.order_types["RISK_MANAGEMENT"]:
                        return self.open_position_with_risk_management(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            risk_amount=risk_amount,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                            use_trailing_stop=self.use_trailing_stop,
                            trailing_stop_callback_rate=trailing_stop_callback_rate,
                        )
                    elif self.order_types["TRAILING_STOP"] and self.use_trailing_stop:
                        return self.open_position_with_trailing_stop(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            callback_rate=trailing_stop_callback_rate,
                        )
                    elif (
                        self.order_types["OCO"]
                        and use_oco
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_oco(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    elif (
                        self.order_types["SL_TP"]
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_sl_tp(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    else:
                        return self.open_position(symbol, "BUY", leverage)
                elif not has_position:
                    # LONG pozisyonu aç
                    logger.info(f"{symbol} için LONG pozisyonu açılıyor")

                    # Emir tipini belirle
                    if self.order_types["RISK_MANAGEMENT"]:
                        return self.open_position_with_risk_management(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            risk_amount=risk_amount,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                            use_trailing_stop=self.use_trailing_stop,
                            trailing_stop_callback_rate=trailing_stop_callback_rate,
                        )
                    elif self.order_types["TRAILING_STOP"] and self.use_trailing_stop:
                        return self.open_position_with_trailing_stop(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            callback_rate=trailing_stop_callback_rate,
                        )
                    elif (
                        self.order_types["OCO"]
                        and use_oco
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_oco(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    elif (
                        self.order_types["SL_TP"]
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_sl_tp(
                            symbol=symbol,
                            side="BUY",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    else:
                        return self.open_position(symbol, "BUY", leverage)
                else:
                    logger.info(f"{symbol} için zaten LONG pozisyonu var")
                    return None

            elif signal == "SHORT":
                if has_position and float(position["positionAmt"]) > 0:
                    # LONG pozisyonu kapat
                    logger.info(
                        f"{symbol} için LONG pozisyonu kapatılıyor (SHORT sinyali)"
                    )
                    self.close_position(symbol)
                    # SHORT pozisyonu aç
                    logger.info(f"{symbol} için SHORT pozisyonu açılıyor")

                    # Emir tipini belirle
                    if self.order_types["RISK_MANAGEMENT"]:
                        return self.open_position_with_risk_management(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            risk_amount=risk_amount,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                            use_trailing_stop=self.use_trailing_stop,
                            trailing_stop_callback_rate=trailing_stop_callback_rate,
                        )
                    elif self.order_types["TRAILING_STOP"] and self.use_trailing_stop:
                        return self.open_position_with_trailing_stop(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            callback_rate=trailing_stop_callback_rate,
                        )
                    elif (
                        self.order_types["OCO"]
                        and use_oco
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_oco(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    elif (
                        self.order_types["SL_TP"]
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_sl_tp(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    else:
                        return self.open_position(symbol, "SELL", leverage)
                elif not has_position:
                    # SHORT pozisyonu aç
                    logger.info(f"{symbol} için SHORT pozisyonu açılıyor")

                    # Emir tipini belirle
                    if self.order_types["RISK_MANAGEMENT"]:
                        return self.open_position_with_risk_management(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            risk_amount=risk_amount,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                            use_trailing_stop=self.use_trailing_stop,
                            trailing_stop_callback_rate=trailing_stop_callback_rate,
                        )
                    elif self.order_types["TRAILING_STOP"] and self.use_trailing_stop:
                        return self.open_position_with_trailing_stop(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            callback_rate=trailing_stop_callback_rate,
                        )
                    elif (
                        self.order_types["OCO"]
                        and use_oco
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_oco(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    elif (
                        self.order_types["SL_TP"]
                        and stop_loss_percent
                        and take_profit_percent
                    ):
                        return self.open_position_with_sl_tp(
                            symbol=symbol,
                            side="SELL",
                            leverage=leverage,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                        )
                    else:
                        return self.open_position(symbol, "SELL", leverage)
                else:
                    logger.info(f"{symbol} için zaten SHORT pozisyonu var")
                    return None

            elif signal == "HOLD":
                logger.info(f"{symbol} için HOLD sinyali, işlem yapılmıyor")
                return None

            else:
                logger.warning(f"{symbol} için geçersiz sinyal: {signal}")
                return None

        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {signal} sinyali işlenirken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def open_position_with_sl_tp(
        self,
        symbol: str,
        side: str,
        leverage: int,
        stop_loss_percent: float,
        take_profit_percent: float,
        min_notional: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Stop Loss ve Take Profit ile yeni bir pozisyon açar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            leverage: Kaldıraç oranı
            stop_loss_percent: Stop Loss yüzdesi (örn. 2.0 = %2)
            take_profit_percent: Take Profit yüzdesi (örn. 3.0 = %3)
            min_notional: Minimum nominal değer (varsayılan: 5.0)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            # Mevcut emirleri iptal et
            self.client.cancel_all_orders(symbol)

            # Kaldıracı ayarla
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

            # Minimum miktarı hesapla
            min_qty = self.client.calculate_min_quantity(symbol, min_notional)
            if not min_qty:
                raise ValueError(f"{symbol} için minimum miktar hesaplanamadı")

            # Emir miktarını hesapla (minimum miktarın %10 fazlası)
            order_qty = float(
                Decimal(str(min_qty * 1.1)).quantize(
                    Decimal(
                        "0." + "0" * self.client.get_futures_quantity_precision(symbol)
                    ),
                    rounding=ROUND_DOWN,
                )
            )

            # Mevcut fiyatı al
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            # Stop Loss ve Take Profit fiyatlarını hesapla
            if side == "BUY":
                stop_loss_price = current_price * (1 - stop_loss_percent / 100)
                take_profit_price = current_price * (1 + take_profit_percent / 100)
            else:  # SELL
                stop_loss_price = current_price * (1 + stop_loss_percent / 100)
                take_profit_price = current_price * (1 - take_profit_percent / 100)

            # Ana emri oluştur
            order = self.client.futures_create_order(
                symbol=symbol, side=side, order_type="MARKET", quantity=order_qty
            )

            # Stop Loss ve Take Profit emirlerini oluştur
            stop_loss_order = self.client.create_stop_loss_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                quantity=order_qty,
                stop_price=stop_loss_price,
            )

            take_profit_order = self.client.create_take_profit_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                quantity=order_qty,
                take_profit_price=take_profit_price,
            )

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=order_qty,
                order_id=str(order.get("orderId")),
                leverage=leverage,
                is_open=True,
            )

            self.send_notification(
                f"🔔 {symbol} {side} pozisyonu açıldı:\n"
                f"Giriş: {current_price:.8f}\n"
                f"Stop Loss: {stop_loss_price:.8f} ({stop_loss_percent}%)\n"
                f"Take Profit: {take_profit_price:.8f} ({take_profit_percent}%)"
            )

            return {
                "entry_order": order,
                "stop_loss_order": stop_loss_order,
                "take_profit_order": take_profit_order,
            }

        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {side} pozisyonu açılırken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

    def open_position_with_oco(
        self,
        symbol: str,
        side: str,
        leverage: int,
        stop_loss_percent: float,
        take_profit_percent: float,
        min_notional: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """
        OCO (One-Cancels-Other) emri ile yeni bir pozisyon açar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            leverage: Kaldıraç oranı
            stop_loss_percent: Stop Loss yüzdesi (örn. 2.0 = %2)
            take_profit_percent: Take Profit yüzdesi (örn. 3.0 = %3)
            min_notional: Minimum nominal değer (varsayılan: 5.0)

        Returns:
            Optional[Dict[str, Any]]: Emir bilgileri veya None (hata durumunda)
        """
        try:
            # Mevcut emirleri iptal et
            self.client.cancel_all_orders(symbol)

            # Kaldıracı ayarla
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

            # Minimum miktarı hesapla
            min_qty = self.client.calculate_min_quantity(symbol, min_notional)
            if not min_qty:
                raise ValueError(f"{symbol} için minimum miktar hesaplanamadı")

            # Emir miktarını hesapla (minimum miktarın %10 fazlası)
            order_qty = float(
                Decimal(str(min_qty * 1.1)).quantize(
                    Decimal(
                        "0." + "0" * self.client.get_futures_quantity_precision(symbol)
                    ),
                    rounding=ROUND_DOWN,
                )
            )

            # Mevcut fiyatı al
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            # Stop Loss ve Take Profit fiyatlarını hesapla
            if side == "BUY":
                stop_loss_price = current_price * (1 - stop_loss_percent / 100)
                take_profit_price = current_price * (1 + take_profit_percent / 100)
            else:  # SELL
                stop_loss_price = current_price * (1 + stop_loss_percent / 100)
                take_profit_price = current_price * (1 - take_profit_percent / 100)

            # Ana emri oluştur
            order = self.client.futures_create_order(
                symbol=symbol, side=side, order_type="MARKET", quantity=order_qty
            )

            # OCO emrini oluştur
            oco_order = self.client.create_oco_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                quantity=order_qty,
                stop_price=stop_loss_price,
                take_profit_price=take_profit_price,
            )

            # Bildirim gönder
            self.send_trade_notification(
                symbol=symbol,
                side=side,
                quantity=order_qty,
                order_id=str(order.get("orderId")),
                leverage=leverage,
                is_open=True,
            )

            self.send_notification(
                f"🔔 {symbol} {side} pozisyonu açıldı (OCO):\n"
                f"Giriş: {current_price:.8f}\n"
                f"Stop Loss: {stop_loss_price:.8f} ({stop_loss_percent}%)\n"
                f"Take Profit: {take_profit_price:.8f} ({take_profit_percent}%)"
            )

            return {"entry_order": order, "oco_order": oco_order}

        except Exception as e:
            error_msg = (
                f"❌ {symbol} için {side} pozisyonu açılırken hata oluştu: {str(e)}"
            )
            logger.error(error_msg)
            self.send_notification(error_msg)
            return None

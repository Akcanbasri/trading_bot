"""
Binance API istemcisi.

Bu modül, Binance API ile etkileşim kurmak için gerekli fonksiyonları sağlar.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, ROUND_DOWN
from loguru import logger
from binance.client import Client
from binance.exceptions import BinanceAPIException
from src.utils.log_throttler import LogThrottler


class BinanceClient:
    """
    Binance API istemcisi sınıfı.

    Binance API ile etkileşim kurmak için gerekli metodları sağlar.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Binance API istemcisini başlatır.

        Args:
            api_key: API anahtarı (opsiyonel)
            api_secret: API gizli anahtarı (opsiyonel)
        """
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("API anahtarları bulunamadı")

        self.client = Client(self.api_key, self.api_secret)
        self.server_time_offset = self._calculate_server_time_offset()

        # Initialize log throttler with default 60-second interval
        self.log_throttler = LogThrottler(default_interval=60.0)

        # Set custom intervals for specific log types
        self.log_throttler.set_interval(
            "price_check", 30.0
        )  # Price checks every 30 seconds
        self.log_throttler.set_interval(
            "position_check", 60.0
        )  # Position checks every 60 seconds
        self.log_throttler.set_interval(
            "balance_check", 300.0
        )  # Balance checks every 5 minutes

        logger.info("Binance API istemcisi başlatıldı")

    def _calculate_server_time_offset(self) -> int:
        """
        Sunucu zamanı farkını hesaplar.

        Returns:
            int: Sunucu zamanı farkı (milisaniye)
        """
        try:
            server_time = self.client.get_server_time()
            local_time = int(time.time() * 1000)
            offset = server_time["serverTime"] - local_time
            logger.debug(f"Sunucu zamanı farkı: {offset} ms")
            return offset
        except Exception as e:
            logger.error(f"Sunucu zamanı farkı hesaplanırken hata oluştu: {e}")
            return 0

    def get_server_time(self, is_futures: bool = False) -> int:
        """
        Binance sunucu zamanını döndürür.

        Args:
            is_futures: Futures API kullanılıyor mu (varsayılan: False)

        Returns:
            int: Sunucu zamanı (milisaniye)
        """
        try:
            server_time = self.client.get_server_time()
            local_time = int(time.time() * 1000)
            offset = server_time["serverTime"] - local_time

            # Use throttled logging for server time offset
            self.log_throttler.log(
                "server_time",
                f"{'Futures' if is_futures else 'Spot'} Server time offset: {offset}ms",
                level="debug",
            )

            return server_time["serverTime"]
        except Exception as e:
            logger.error(f"Sunucu zamanı alınırken hata oluştu: {e}")
            return int(time.time() * 1000) + self.server_time_offset

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Mevcut fiyatı alır.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")

        Returns:
            Optional[float]: Mevcut fiyat veya None (hata durumunda)
        """
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])

            # Use throttled logging for price updates
            self.log_throttler.log(
                f"price_{symbol}", f"{symbol} mevcut fiyat: {price}", level="debug"
            )

            return price
        except Exception as e:
            logger.error(f"{symbol} için mevcut fiyat alınırken hata oluştu: {e}")
            return None

    def get_futures_quantity_precision(self, symbol: str) -> int:
        """
        Futures miktar hassasiyetini alır.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")

        Returns:
            int: Miktar hassasiyeti
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next(
                (s for s in exchange_info["symbols"] if s["symbol"] == symbol), None
            )
            if not symbol_info:
                raise ValueError(f"{symbol} için sembol bilgisi bulunamadı")

            quantity_precision = symbol_info["quantityPrecision"]

            # Use throttled logging for precision info
            self.log_throttler.log(
                f"precision_{symbol}",
                f"{symbol} miktar hassasiyeti: {quantity_precision}",
                level="debug",
            )

            return quantity_precision
        except Exception as e:
            logger.error(f"{symbol} için miktar hassasiyeti alınırken hata oluştu: {e}")
            return 8  # Varsayılan hassasiyet

    def calculate_min_quantity(
        self, symbol: str, min_notional: float
    ) -> Optional[float]:
        """
        Minimum miktarı hesaplar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            min_notional: Minimum nominal değer

        Returns:
            Optional[float]: Minimum miktar veya None (hata durumunda)
        """
        try:
            current_price = self.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            min_qty = min_notional / current_price
            precision = self.get_futures_quantity_precision(symbol)
            min_qty = float(
                Decimal(str(min_qty)).quantize(
                    Decimal("0." + "0" * precision), rounding=ROUND_DOWN
                )
            )

            # Use throttled logging for min quantity
            self.log_throttler.log(
                f"min_qty_{symbol}",
                f"{symbol} minimum miktar: {min_qty}",
                level="debug",
            )

            return min_qty
        except Exception as e:
            logger.error(f"{symbol} için minimum miktar hesaplanırken hata oluştu: {e}")
            return None

    def futures_change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Kaldıraç oranını değiştirir.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            leverage: Kaldıraç oranı

        Returns:
            Dict[str, Any]: İşlem sonucu
        """
        try:
            result = self.client.futures_change_leverage(
                symbol=symbol, leverage=leverage
            )

            # Use throttled logging for leverage changes
            self.log_throttler.log(
                f"leverage_{symbol}",
                f"{symbol} kaldıraç oranı {leverage}x olarak ayarlandı",
                level="debug",
            )

            return result
        except Exception as e:
            logger.error(
                f"{symbol} için kaldıraç oranı değiştirilirken hata oluştu: {e}"
            )
            raise

    def futures_create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        reduce_only: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Futures emri oluşturur.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            order_type: Emir tipi ("MARKET", "LIMIT", vb.)
            quantity: İşlem miktarı
            reduce_only: Sadece pozisyon kapatma emri mi (varsayılan: False)
            **kwargs: Diğer parametreler

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "reduceOnly": reduce_only,
                **kwargs,
            }

            # Always log order creation (not throttled)
            logger.debug(f"Futures emri oluşturuluyor: {params}")

            order = self.client.futures_create_order(**params)

            # Always log successful order creation (not throttled)
            logger.info(f"Futures emri başarıyla oluşturuldu: {order}")

            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"Futures emri oluşturulurken hata oluştu: {e}")
            raise

    def get_futures_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Futures pozisyon bilgilerini alır.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")

        Returns:
            Optional[Dict[str, Any]]: Pozisyon bilgileri veya None (hata durumunda)
        """
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            if not positions:
                # Use throttled logging for position checks
                self.log_throttler.log(
                    f"position_{symbol}",
                    f"{symbol} için pozisyon bilgisi bulunamadı",
                    level="info",
                )
                return None

            position = positions[0]

            # Use throttled logging for position details
            self.log_throttler.log(
                f"position_{symbol}",
                f"{symbol} pozisyon bilgileri: {position}",
                level="debug",
            )

            return position
        except Exception as e:
            logger.error(f"{symbol} için pozisyon bilgileri alınırken hata oluştu: {e}")
            return None

    def get_futures_balance(self) -> Dict[str, float]:
        """
        Futures hesap bakiyesini döndürür.

        Returns:
            Dict[str, float]: Bakiye bilgileri
        """
        try:
            account = self.client.futures_account_balance()
            balances = {}
            for balance in account:
                if float(balance["balance"]) > 0:
                    balances[balance["asset"]] = float(balance["balance"])

            # Use throttled logging for balance checks
            self.log_throttler.log(
                "balance", f"Futures hesap bakiyesi: {balances}", level="debug"
            )

            return balances
        except Exception as e:
            logger.error(f"Bakiye bilgileri alınırken hata oluştu: {e}")
            return {}

    def calculate_position_size(
        self, symbol: str, risk_amount: float, stop_loss_percent: float, leverage: int
    ) -> Optional[float]:
        """
        Risk bazlı pozisyon büyüklüğünü hesaplar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            risk_amount: Risk edilecek miktar (USDT)
            stop_loss_percent: Stop Loss yüzdesi (örn. 2.0 = %2)
            leverage: Kaldıraç oranı

        Returns:
            Optional[float]: Pozisyon büyüklüğü veya None (hata durumunda)
        """
        try:
            # Mevcut fiyatı al
            current_price = self.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"{symbol} için mevcut fiyat alınamadı")

            # Stop Loss fiyatını hesapla
            stop_loss_price = current_price * (stop_loss_percent / 100)

            # Risk bazlı pozisyon büyüklüğünü hesapla
            position_size = (risk_amount * leverage) / stop_loss_price

            # Miktar hassasiyetine göre yuvarla
            precision = self.get_futures_quantity_precision(symbol)
            position_size = float(
                Decimal(str(position_size)).quantize(
                    Decimal("0." + "0" * precision), rounding=ROUND_DOWN
                )
            )

            # Use throttled logging for position size calculations
            self.log_throttler.log(
                f"position_size_{symbol}",
                f"{symbol} için risk bazlı pozisyon büyüklüğü hesaplandı: {position_size} "
                f"(risk: {risk_amount} USDT, kaldıraç: {leverage}x, SL: {stop_loss_percent}%)",
                level="debug",
            )

            return position_size
        except Exception as e:
            logger.error(f"Pozisyon büyüklüğü hesaplanırken hata oluştu: {e}")
            return None

    def get_futures_position_risk(
        self, symbol: str, position_size: float, entry_price: float, leverage: int
    ) -> Dict[str, float]:
        """
        Pozisyon risk metriklerini hesaplar.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            position_size: Pozisyon büyüklüğü
            entry_price: Giriş fiyatı
            leverage: Kaldıraç oranı

        Returns:
            Dict[str, float]: Risk metrikleri
        """
        try:
            # Pozisyon değerini hesapla
            position_value = position_size * entry_price

            # Kullanılan marjini hesapla
            used_margin = position_value / leverage

            # Maksimum kayıp miktarını hesapla
            max_loss = used_margin

            # Risk/Ödül oranını hesapla (varsayılan olarak 1:2)
            risk_reward_ratio = 2.0

            # Beklenen kâr miktarını hesapla
            expected_profit = max_loss * risk_reward_ratio

            risk_metrics = {
                "position_value": position_value,
                "used_margin": used_margin,
                "max_loss": max_loss,
                "expected_profit": expected_profit,
                "risk_reward_ratio": risk_reward_ratio,
            }

            # Use throttled logging for risk metrics
            self.log_throttler.log(
                f"risk_metrics_{symbol}",
                f"{symbol} için risk metrikleri hesaplandı: {risk_metrics}",
                level="debug",
            )

            return risk_metrics
        except Exception as e:
            logger.error(f"Risk metrikleri hesaplanırken hata oluştu: {e}")
            return {}

    def close(self) -> None:
        """
        API bağlantısını kapatır.
        """
        try:
            self.client.close_connection()
            logger.info("API bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"API bağlantısı kapatılırken hata oluştu: {e}")

    def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        reduce_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Stop Loss emri oluşturur.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            stop_price: Stop fiyatı
            reduce_only: Sadece pozisyon kapatma emri mi (varsayılan: True)

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": "STOP_MARKET",
                "quantity": quantity,
                "stopPrice": stop_price,
                "reduceOnly": reduce_only,
            }

            # Always log order creation (not throttled)
            logger.debug(f"Stop Loss emri oluşturuluyor: {params}")

            order = self.client.futures_create_order(**params)

            # Always log successful order creation (not throttled)
            logger.info(f"Stop Loss emri başarıyla oluşturuldu: {order}")

            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"Stop Loss emri oluşturulurken hata oluştu: {e}")
            raise

    def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        reduce_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Take Profit emri oluşturur.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            take_profit_price: Take Profit fiyatı
            reduce_only: Sadece pozisyon kapatma emri mi (varsayılan: True)

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": "TAKE_PROFIT_MARKET",
                "quantity": quantity,
                "stopPrice": take_profit_price,
                "reduceOnly": reduce_only,
            }

            # Always log order creation (not throttled)
            logger.debug(f"Take Profit emri oluşturuluyor: {params}")

            order = self.client.futures_create_order(**params)

            # Always log successful order creation (not throttled)
            logger.info(f"Take Profit emri başarıyla oluşturuldu: {order}")

            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"Take Profit emri oluşturulurken hata oluştu: {e}")
            raise

    def create_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        take_profit_price: float,
        reduce_only: bool = True,
    ) -> Dict[str, Any]:
        """
        OCO (One-Cancels-Other) emri oluşturur.
        Bu emir, Stop Loss ve Take Profit emirlerini birlikte oluşturur.
        Biri tetiklendiğinde diğeri otomatik olarak iptal edilir.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            stop_price: Stop Loss fiyatı
            take_profit_price: Take Profit fiyatı
            reduce_only: Sadece pozisyon kapatma emri mi (varsayılan: True)

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "stopPrice": stop_price,
                "stopLimitPrice": stop_price,  # Stop Limit fiyatı Stop fiyatı ile aynı
                "stopLimitTimeInForce": "GTC",
                "takeProfitPrice": take_profit_price,
                "reduceOnly": reduce_only,
            }

            # Always log order creation (not throttled)
            logger.debug(f"OCO emri oluşturuluyor: {params}")

            order = self.client.futures_create_oco_order(**params)

            # Always log successful order creation (not throttled)
            logger.info(f"OCO emri başarıyla oluşturuldu: {order}")

            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"OCO emri oluşturulurken hata oluştu: {e}")
            raise

    def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """
        Belirtilen sembol için tüm emirleri iptal eder.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")

        Returns:
            Dict[str, Any]: İptal işlemi sonucu
        """
        try:
            # Always log order cancellation (not throttled)
            logger.debug(f"{symbol} için tüm emirler iptal ediliyor")

            result = self.client.futures_cancel_all_open_orders(symbol=symbol)

            # Always log successful cancellation (not throttled)
            logger.info(f"{symbol} için tüm emirler başarıyla iptal edildi")

            return result
        except Exception as e:
            logger.error(f"{symbol} için emirler iptal edilirken hata oluştu: {e}")
            raise

    def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        callback_rate: float,
        reduce_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Trailing Stop emri oluşturur.

        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            callback_rate: Geri çağırma oranı (örn. 1.0 = %1)
            reduce_only: Sadece pozisyon kapatma emri mi (varsayılan: True)

        Returns:
            Dict[str, Any]: Emir bilgileri
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": "TRAILING_STOP_MARKET",
                "quantity": quantity,
                "callbackRate": callback_rate,
                "reduceOnly": reduce_only,
            }

            # Always log order creation (not throttled)
            logger.debug(f"Trailing Stop emri oluşturuluyor: {params}")

            order = self.client.futures_create_order(**params)

            # Always log successful order creation (not throttled)
            logger.info(f"Trailing Stop emri başarıyla oluşturuldu: {order}")

            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"Trailing Stop emri oluşturulurken hata oluştu: {e}")
            raise

"""
Binance API için client wrapper.
"""

from typing import Dict, List, Optional, Any, Union
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger
import pandas as pd
import time
from datetime import datetime, timedelta
import requests
import hmac
import hashlib


class BinanceClient:
    """Binance API istemcisi wrapper sınıfı."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Binance API istemcisi başlatma.

        Args:
            api_key: Binance API anahtarı
            api_secret: Binance API gizli anahtarı
            testnet: Testnet modunu kullan (varsayılan: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json;charset=utf-8",
                "X-MBX-APIKEY": self.api_key,
            }
        )
        self.time_offset = 0
        self._init_time_offset()

        # Binance client'ı başlat
        self.client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)

        logger.info(f"Binance client başlatıldı. Testnet: {testnet}")

    def _init_time_offset(self):
        """Initialize time offset between local and server time"""
        try:
            for i in range(3):  # Try 3 times
                server_time = self.get_server_time()
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
                # If offset is small enough, we're good
                if abs(self.time_offset) < 1000:
                    break
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error initializing time offset: {e}")
            self.time_offset = 0

    def get_server_time(self):
        """Get Binance server time in milliseconds"""
        try:
            response = self.session.get("https://fapi.binance.com/fapi/v1/time")
            response.raise_for_status()
            return response.json()["serverTime"]
        except Exception as e:
            logger.error(f"Error getting server time: {e}")
            return int(time.time() * 1000)  # Fallback to local time

    def _get_timestamp(self) -> int:
        """
        Sunucu zamanı ile senkronize timestamp döndürür.

        Returns:
            int: Timestamp (milisaniye)
        """
        return int(time.time() * 1000) + self.time_offset

    def _get_futures_timestamp(self) -> int:
        """
        Futures API için senkronize timestamp döndürür.

        Returns:
            int: Timestamp (milisaniye)
        """
        try:
            # Get current time and apply the offset we calculated during initialization
            return int(time.time() * 1000) + self.time_offset
        except Exception as e:
            logger.error(f"Error getting futures timestamp: {e}")
            return int(time.time() * 1000)  # Fallback to local time

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Borsa bilgisini alır.

        Returns:
            Dict: Borsa bilgisi
        """
        try:
            return self.client.get_exchange_info()
        except BinanceAPIException as e:
            logger.error(f"Borsa bilgisi alınamadı: {e}")
            raise

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Sembol bilgisini alır.

        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")

        Returns:
            Dict: Sembol bilgisi
        """
        try:
            return self.client.get_symbol_info(symbol)
        except BinanceAPIException as e:
            logger.error(f"{symbol} sembol bilgisi alınamadı: {e}")
            raise

    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
        limit: int = 500,
    ) -> List[List[Any]]:
        """
        Geçmiş kline/candlestick verilerini alır.

        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            interval: Zaman aralığı (örn. "1d", "4h", "1h", "15m", "5m", "1m")
            start_str: Başlangıç zamanı (örn. "1 Jan, 2020")
            end_str: Bitiş zamanı (örn. "1 Jan, 2021")
            limit: Sonuç sayısı limiti

        Returns:
            List: Kline verileri listesi
        """
        try:
            return self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str,
                limit=limit,
            )
        except BinanceAPIException as e:
            logger.error(f"{symbol} için kline verileri alınamadı: {e}")
            raise

    def get_account(self) -> Dict[str, Any]:
        """
        Hesap bilgilerini alır.

        Returns:
            Dict: Hesap bilgileri
        """
        try:
            return self.client.get_account()
        except BinanceAPIException as e:
            logger.error(f"Hesap bilgisi alınamadı: {e}")
            raise

    def get_asset_balance(self, asset: str) -> Dict[str, str]:
        """
        Belirli bir varlık için bakiye bilgisini alır.

        Args:
            asset: Varlık sembolü (örn. "BTC", "USDT")

        Returns:
            Dict: Varlık bakiye bilgisi
        """
        try:
            return self.client.get_asset_balance(asset=asset)
        except BinanceAPIException as e:
            logger.error(f"{asset} için bakiye bilgisi alınamadı: {e}")
            raise

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Futures emir oluşturur.

        Args:
            symbol: İşlem sembolü
            side: İşlem yönü (BUY/SELL)
            order_type: Emir tipi (LIMIT/MARKET/STOP/TAKE_PROFIT vs.)
            quantity: İşlem miktarı
            price: Emir fiyatı (LIMIT emirleri için)
            time_in_force: Emir geçerlilik süresi (GTC/IOC/FOK)
            reduce_only: Sadece pozisyon kapatma
            **kwargs: Diğer parametreler

        Returns:
            Dict: API yanıtı
        """
        try:
            # Round quantity to required precision
            quantity = self.round_quantity_to_precision(symbol, quantity)

            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "reduceOnly": reduce_only,
            }

            if order_type == "LIMIT":
                if price is None:
                    raise ValueError("Price is required for limit orders")
                params["price"] = price
                params["timeInForce"] = time_in_force

            params.update(kwargs)

            self.logger.info(f"Creating {order_type} order: {params}")
            return self.client.futures_create_order(**params)

        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            raise

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Açık emirleri alır.

        Args:
            symbol: İşlem sembolü (opsiyonel)

        Returns:
            List: Açık emirler listesi
        """
        try:
            return self.client.get_open_orders(symbol=symbol)
        except BinanceAPIException as e:
            logger.error(f"Açık emirler alınamadı: {e}")
            raise

    def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bir emri iptal eder.

        Args:
            symbol: İşlem sembolü
            order_id: Emir ID'si (opsiyonel)
            orig_client_order_id: Orijinal client emir ID'si (opsiyonel)

        Returns:
            Dict: İptal edilen emir bilgisi
        """
        try:
            return self.client.cancel_order(
                symbol=symbol, orderId=order_id, origClientOrderId=orig_client_order_id
            )
        except BinanceAPIException as e:
            logger.error(f"Emir iptal edilemedi: {e}")
            raise

    def get_futures_account_balance(self) -> Dict[str, float]:
        """
        Futures hesap bakiyesini alır.

        Returns:
            Dict[str, float]: Bakiye bilgileri
        """
        try:
            account = self.client.futures_account_balance()
            total_balance = float(account[0]["balance"])
            available_balance = float(account[0]["withdrawAvailable"])

            return {"total": total_balance, "available": available_balance}
        except BinanceAPIException as e:
            logger.error(f"Futures bakiye bilgisi alınamadı: {e}")
            raise

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Kaldıraç oranını ayarlar.

        Args:
            symbol: İşlem sembolü
            leverage: Kaldıraç oranı

        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"{symbol} için kaldıraç {leverage}x olarak ayarlandı")
            return True
        except BinanceAPIException as e:
            logger.error(f"Kaldıraç ayarlanamadı: {e}")
            return False

    def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """
        Marj tipini ayarlar (ISOLATED veya CROSSED).

        Args:
            symbol: İşlem sembolü
            margin_type: Marj tipi ('ISOLATED' veya 'CROSSED')

        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            self.client.futures_change_margin_type(
                symbol=symbol, marginType=margin_type
            )
            logger.info(f"{symbol} için marj tipi {margin_type} olarak ayarlandı")
            return True
        except BinanceAPIException as e:
            logger.error(f"Marj tipi ayarlanamadı: {e}")
            return False

    def open_futures_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Futures pozisyonu açar.

        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ('BUY' veya 'SELL')
            quantity: İşlem miktarı
            leverage: Kaldıraç oranı
            stop_loss: Stop-loss fiyatı
            take_profit: Take-profit fiyatı

        Returns:
            Dict[str, Any]: İşlem bilgileri
        """
        try:
            # Kaldıracı ayarla
            self.set_leverage(symbol, leverage)

            # Ana emri gönder
            order = self.client.futures_create_order(
                symbol=symbol, side=side, type="MARKET", quantity=quantity
            )

            # Stop-loss emri
            if stop_loss:
                sl_side = "SELL" if side == "BUY" else "BUY"
                self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type="STOP_MARKET",
                    stopPrice=stop_loss,
                    closePosition=True,
                )

            # Take-profit emri
            if take_profit:
                tp_side = "SELL" if side == "BUY" else "BUY"
                self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type="TAKE_PROFIT_MARKET",
                    stopPrice=take_profit,
                    closePosition=True,
                )

            logger.info(
                f"Futures pozisyonu açıldı: {symbol} {side} {quantity}@{leverage}x"
            )
            return order

        except BinanceAPIException as e:
            logger.error(f"Futures pozisyonu açılamadı: {e}")
            raise

    def close_futures_position(self, symbol: str) -> bool:
        """
        Futures pozisyonunu kapatır.

        Args:
            symbol: İşlem sembolü

        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            position = self.client.futures_position_information(symbol=symbol)[0]
            if float(position["positionAmt"]) != 0:
                side = "SELL" if float(position["positionAmt"]) > 0 else "BUY"
                quantity = abs(float(position["positionAmt"]))

                self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=quantity,
                    reduceOnly=True,
                )

                logger.info(f"Futures pozisyonu kapatıldı: {symbol}")
                return True
            return False

        except BinanceAPIException as e:
            logger.error(f"Futures pozisyonu kapatılamadı: {e}")
            return False

    def get_futures_position(self, symbol: str) -> Dict[str, Any]:
        """
        Futures pozisyon bilgilerini alır.

        Args:
            symbol: İşlem sembolü

        Returns:
            Dict[str, Any]: Pozisyon bilgileri
        """
        try:
            position = self.client.futures_position_information(symbol=symbol)[0]
            return {
                "symbol": position["symbol"],
                "position_amt": float(position["positionAmt"]),
                "entry_price": float(position["entryPrice"]),
                "unrealized_pnl": float(position["unRealizedProfit"]),
                "leverage": int(position["leverage"]),
                "margin_type": position["marginType"],
            }
        except BinanceAPIException as e:
            logger.error(f"Futures pozisyon bilgisi alınamadı: {e}")
            raise

    def get_futures_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Futures kline verilerini alır.

        Args:
            symbol: İşlem sembolü
            interval: Zaman aralığı
            limit: Veri sayısı
            start_time: Başlangıç zamanı
            end_time: Bitiş zamanı

        Returns:
            pd.DataFrame: Kline verileri
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_time,
                endTime=end_time,
            )

            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_volume",
                    "trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            return df

        except BinanceAPIException as e:
            logger.error(f"Futures kline verileri alınamadı: {e}")
            raise

    def futures_change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Futures kaldıraç oranını değiştirir.

        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            leverage: Kaldıraç oranı (1-125)

        Returns:
            Dict: API yanıtı
        """
        try:
            timestamp = self._get_timestamp()
            params = {"symbol": symbol, "leverage": leverage, "timestamp": timestamp}

            # Add signature
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            params["signature"] = signature

            response = self.session.post(
                "https://fapi.binance.com/fapi/v1/leverage", params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error changing leverage: {e}")
            raise

    def futures_create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        position_side: str = "BOTH",
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        stop_price: Optional[float] = None,
        close_position: bool = False,
        activation_price: Optional[float] = None,
        callback_rate: Optional[float] = None,
        working_type: str = "CONTRACT_PRICE",
        price_protect: bool = False,
        new_client_order_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Futures emir oluşturur.

        Args:
            symbol: İşlem sembolü
            side: İşlem yönü (BUY/SELL)
            order_type: Emir tipi (LIMIT/MARKET/STOP/TAKE_PROFIT vs.)
            quantity: İşlem miktarı
            price: Emir fiyatı (LIMIT emirleri için)
            position_side: Pozisyon yönü (BOTH/LONG/SHORT)
            time_in_force: Emir geçerlilik süresi (GTC/IOC/FOK)
            reduce_only: Sadece pozisyon kapatma
            stop_price: Stop fiyatı (STOP/TAKE_PROFIT emirleri için)
            close_position: Pozisyonu kapat
            activation_price: Tetikleme fiyatı (TRAILING_STOP emirleri için)
            callback_rate: Geri çağırma oranı (TRAILING_STOP emirleri için)
            working_type: Çalışma tipi (CONTRACT_PRICE/MARK_PRICE)
            price_protect: Fiyat koruması
            new_client_order_id: Özel emir ID
            **kwargs: Diğer parametreler

        Returns:
            Dict: API yanıtı
        """
        try:
            # Get current server time
            server_time = self.get_server_time()

            # Prepare parameters
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "timestamp": server_time,
            }

            # Add optional parameters based on order type
            if order_type == "LIMIT":
                params.update({"timeInForce": time_in_force, "price": price})
            elif order_type == "MARKET":
                # For MARKET orders, we only need symbol, side, type, and quantity
                pass
            elif order_type in ["STOP", "TAKE_PROFIT"]:
                params.update(
                    {
                        "timeInForce": time_in_force,
                        "price": price,
                        "stopPrice": stop_price,
                    }
                )
            elif order_type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]:
                params.update({"stopPrice": stop_price})
            elif order_type == "TRAILING_STOP_MARKET":
                params.update({"callbackRate": callback_rate})

            # Add other optional parameters if provided
            if position_side != "BOTH":
                params["positionSide"] = position_side
            if reduce_only:
                params["reduceOnly"] = "true"
            if close_position:
                params["closePosition"] = "true"
            if working_type != "CONTRACT_PRICE":
                params["workingType"] = working_type
            if price_protect:
                params["priceProtect"] = "true"
            if new_client_order_id:
                params["newClientOrderId"] = new_client_order_id

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            # Convert boolean values to strings
            for key in params:
                if isinstance(params[key], bool):
                    params[key] = str(params[key]).lower()

            # Create signature
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            params["signature"] = signature

            # Make request
            response = self.session.post(
                "https://fapi.binance.com/fapi/v1/order", params=params
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Futures emri oluşturulamadı: {e}")
            raise

    def futures_get_position_information(
        self, symbol: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Futures pozisyon bilgilerini getirir.

        Args:
            symbol: İşlem sembolü (opsiyonel)

        Returns:
            Union[Dict, List[Dict]]: API yanıtı
        """
        try:
            params = {"timestamp": self._get_timestamp()}
            if symbol:
                params["symbol"] = symbol
            return self.client.futures_position_information(**params)
        except BinanceAPIException as e:
            logger.error(f"Pozisyon bilgileri alınamadı: {e}")
            raise

    def futures_get_account_balance(self) -> List[Dict[str, Any]]:
        """
        Futures hesap bakiyelerini getirir.

        Returns:
            List[Dict]: API yanıtı
        """
        try:
            params = {"timestamp": self._get_timestamp()}
            return self.client.futures_account_balance(**params)
        except BinanceAPIException as e:
            logger.error(f"Futures bakiyeleri alınamadı: {e}")
            raise

    def futures_get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Açık futures emirlerini getirir.

        Args:
            symbol: İşlem sembolü (opsiyonel)

        Returns:
            List[Dict]: API yanıtı
        """
        try:
            params = {"timestamp": self._get_timestamp()}
            if symbol:
                params["symbol"] = symbol
            return self.client.futures_get_open_orders(**params)
        except BinanceAPIException as e:
            logger.error(f"Açık futures emirleri alınamadı: {e}")
            raise

    def close(self):
        """
        Kaynakları temizler ve bağlantıyı kapatır.
        """
        try:
            self.client.close_connection()
            logger.info("Binance client bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"Bağlantı kapatılırken hata oluştu: {e}")

    def get_futures_quantity_precision(self, symbol: str) -> int:
        """Get the quantity precision for a futures symbol.

        Args:
            symbol: The trading pair symbol (e.g. 'DOGEUSDT')

        Returns:
            int: The quantity precision (number of decimal places)
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info["symbols"]:
                if s["symbol"] == symbol:
                    return int(s["quantityPrecision"])
            raise ValueError(f"Symbol {symbol} not found in futures exchange info")
        except Exception as e:
            logger.error(f"Error getting quantity precision for {symbol}: {str(e)}")
            raise

    def round_quantity_to_precision(self, symbol: str, quantity: float) -> float:
        """Round a quantity to the symbol's precision requirements.

        Args:
            symbol: The trading pair symbol (e.g. 'DOGEUSDT')
            quantity: The quantity to round

        Returns:
            float: The rounded quantity
        """
        precision = self.get_futures_quantity_precision(symbol)
        return float(round(quantity, precision))

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        **kwargs,
    ) -> dict:
        """Create a futures order.

        Args:
            symbol: The trading pair symbol (e.g. 'DOGEUSDT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('LIMIT', 'MARKET', etc.)
            quantity: Order quantity
            price: Order price (required for limit orders)
            time_in_force: Time in force ('GTC', 'IOC', 'FOK')
            reduce_only: Whether this order is to reduce position only
            **kwargs: Additional parameters to pass to the API

        Returns:
            dict: Order response from the API
        """
        try:
            # Round quantity to required precision
            quantity = self.round_quantity_to_precision(symbol, quantity)

            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "reduceOnly": reduce_only,
            }

            if order_type == "LIMIT":
                if price is None:
                    raise ValueError("Price is required for limit orders")
                params["price"] = price
                params["timeInForce"] = time_in_force

            params.update(kwargs)

            self.logger.info(f"Creating {order_type} order: {params}")
            return self.client.futures_create_order(**params)

        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            raise

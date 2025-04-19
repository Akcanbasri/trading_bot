"""
Piyasa verilerini toplama ve işleme modülü.
"""

from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import os
import time

from src.api.client import BinanceClient


class MarketDataCollector:
    """Piyasa verilerini toplama ve işleme sınıfı."""

    def __init__(self, client: BinanceClient):
        """
        MarketDataCollector sınıfını başlatır.

        Args:
            client: Binance API istemcisi
        """
        self.client = client
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.price_cache: Dict[str, Dict[str, Any]] = (
            {}
        )  # {symbol: {'price': float, 'timestamp': datetime}}
        self.price_cache_expiry = timedelta(seconds=1)  # Cache prices for 1 second
        self.last_update_time: Dict[str, Dict[str, datetime]] = {}

        # Verify we're using live data
        if not os.getenv("USE_TESTNET", "False").lower() == "true":
            logger.info("Market data collector initialized for live trading")
        else:
            logger.warning(
                "Market data collector initialized for testnet - this should not be used in production!"
            )

    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
        limit: int = 500,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Belirli bir sembol ve zaman aralığı için tarihsel verileri alır.

        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            interval: Zaman aralığı (örn. "1h", "4h", "1d")
            start_str: Başlangıç zamanı (örn. "1 Jan, 2020")
            end_str: Bitiş zamanı (örn. "1 Jan, 2021")
            limit: Sonuç sayısı limiti
            use_cache: Önbellek kullan (varsayılan: True)

        Returns:
            pd.DataFrame: Tarihsel veri DataFrame'i
        """
        # Önbellekten veri getir eğer varsa ve kullanım isteniyorsa
        cache_key = f"{symbol}_{interval}"
        if use_cache and cache_key in self.data_cache:
            logger.debug(f"{symbol} {interval} verileri önbellekten alındı")
            return self.data_cache[cache_key]

        try:
            # Binance'den klines verilerini al
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str,
                limit=limit,
            )

            # Boş veri kontrolü
            if not klines:
                logger.warning(f"{symbol} için {interval} verisi bulunamadı")
                return pd.DataFrame()

            # DataFrame'e dönüştür
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
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            # Veri tiplerini düzenle
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
            ]:
                df[col] = pd.to_numeric(df[col])

            # Zaman damgasını indeks olarak ayarla
            df.set_index("timestamp", inplace=True)

            # Önbelleğe kaydet
            if use_cache:
                self.data_cache[cache_key] = df

            logger.info(
                f"{symbol} için {interval} verisi alındı. Satır sayısı: {len(df)}"
            )
            return df

        except Exception as e:
            logger.error(f"{symbol} için {interval} verisi alınırken hata: {e}")
            return pd.DataFrame()

    def refresh_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Belirtilen sembol ve zaman dilimi için piyasa verisini yeniler.

        Args:
            symbol: Trading sembolü
            timeframe: Zaman dilimi

        Returns:
            pd.DataFrame: Güncellenmiş veri
        """
        try:
            # Get current timestamp
            current_time = datetime.now()

            # Check if we need to refresh based on timeframe
            if (
                symbol in self.last_update_time
                and timeframe in self.last_update_time[symbol]
            ):
                last_update = self.last_update_time[symbol][timeframe]
                time_diff = (current_time - last_update).total_seconds()

                # Define minimum refresh intervals for different timeframes
                min_intervals = {
                    "1m": 30,  # 30 seconds
                    "5m": 60,  # 1 minute
                    "15m": 180,  # 3 minutes
                    "30m": 300,  # 5 minutes
                    "1h": 600,  # 10 minutes
                    "4h": 1800,  # 30 minutes
                    "1d": 3600,  # 1 hour
                }

                min_interval = min_intervals.get(timeframe, 60)  # Default to 1 minute

                if time_diff < min_interval:
                    # Return cached data if refresh interval not reached
                    return self.data_cache[symbol][timeframe]

            # Fetch new data
            new_data = self._fetch_historical_data(symbol, timeframe)

            if new_data is not None and not new_data.empty:
                # Update cache
                if symbol not in self.data_cache:
                    self.data_cache[symbol] = {}
                self.data_cache[symbol][timeframe] = new_data

                # Update last update time
                if symbol not in self.last_update_time:
                    self.last_update_time[symbol] = {}
                self.last_update_time[symbol][timeframe] = current_time

                logger.debug(
                    f"Veri yenilendi - Sembol: {symbol}, Zaman dilimi: {timeframe}, Satır sayısı: {len(new_data)}"
                )
                return new_data
            else:
                logger.warning(
                    f"Veri yenilenemedi - Sembol: {symbol}, Zaman dilimi: {timeframe}"
                )
                return pd.DataFrame()

        except Exception as e:
            logger.error(
                f"Veri yenileme hatası - Sembol: {symbol}, Zaman dilimi: {timeframe}, Hata: {str(e)}"
            )
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")

        Returns:
            float: Current price
        """
        try:
            current_time = time.time()

            # Check cache first
            if symbol in self.price_cache:
                cache_data = self.price_cache[symbol]
                # Check if cache is still valid (less than 1 second old)
                if current_time - cache_data["timestamp"] < 1.0:  # 1 second expiry
                    logger.debug(
                        f"Using cached price for {symbol}: {cache_data['price']}"
                    )
                    return cache_data["price"]

            # Get fresh price from Binance
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])

            # Update cache
            self.price_cache[symbol] = {"price": price, "timestamp": current_time}

            logger.debug(f"Updated price for {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            # Return cached price if available
            if symbol in self.price_cache:
                logger.warning(f"Using stale cached price for {symbol} due to error")
                return self.price_cache[symbol]["price"]
            raise

    def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, List]:
        """
        Bir sembol için emir defterini alır.

        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            limit: Alınacak seviye sayısı

        Returns:
            Dict: Emir defteri sözlüğü
        """
        try:
            order_book = self.client.get_order_book(symbol=symbol, limit=limit)
            return order_book
        except Exception as e:
            logger.error(f"{symbol} için emir defteri alınamadı: {e}")
            raise

    def _fetch_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Belirtilen sembol ve zaman dilimi için tarihsel verileri getirir.

        Args:
            symbol: Trading sembolü
            timeframe: Zaman dilimi

        Returns:
            pd.DataFrame: Tarihsel veri DataFrame'i
        """
        try:
            # Map timeframe to Binance interval format
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
            }

            interval = interval_map.get(timeframe, "15m")

            # Get historical data from Binance
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                limit=500,  # Get enough data for indicators
            )

            if not klines:
                logger.warning(f"{symbol} için {timeframe} verisi bulunamadı")
                return pd.DataFrame()

            # Convert to DataFrame
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
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Convert numeric columns
            numeric_columns = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
            ]
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Set timestamp as index
            df.set_index("timestamp", inplace=True)

            # Sort by timestamp
            df.sort_index(inplace=True)

            logger.info(
                f"{symbol} için {timeframe} verisi alındı. Satır sayısı: {len(df)}"
            )
            return df

        except Exception as e:
            logger.error(f"{symbol} için {timeframe} verisi alınırken hata: {str(e)}")
            return pd.DataFrame()

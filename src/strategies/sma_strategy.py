"""
Simple Moving Average (SMA) trading strategy implementation.
"""

import pandas as pd
from loguru import logger
from typing import Optional, Dict, Any
from src.api.client import BinanceClient
from src.api.binance_websocket import BinanceWebSocket
from src.exceptions.insufficient_data_error import InsufficientDataError


class SMAStrategy:
    def __init__(
        self,
        client: BinanceClient,
        symbol: str,
        timeframe: str,
        short_period: int = 20,
        long_period: int = 50,
    ):
        """
        SMA stratejisini başlatır.

        Args:
            client: Binance API client
            symbol: Trading sembolü (örn. "BTCUSDT")
            timeframe: Zaman dilimi (örn. "1h", "4h", "1d")
            short_period: Kısa SMA periyodu
            long_period: Uzun SMA periyodu
        """
        self.client = client
        self.symbol = symbol
        self.timeframe = timeframe
        self.short_period = short_period
        self.long_period = long_period
        self.historical_data = None
        self.current_price = None
        self.websocket = BinanceWebSocket()

        # WebSocket bağlantısını başlat ve fiyat güncellemelerine abone ol
        self.websocket.subscribe_to_price_updates(symbol, self._handle_price_update)
        self.update_historical_data()

        logger.info(f"SMA stratejisi başlatıldı: {symbol} {timeframe}")

    def _handle_price_update(self, price: float):
        """
        WebSocket üzerinden gelen fiyat güncellemelerini işler.

        Args:
            price: Güncel fiyat
        """
        self.current_price = price
        logger.debug(f"{self.symbol} için fiyat güncellendi: {price}")

    def update_historical_data(self):
        """
        Tarihsel fiyat verilerini günceller.
        """
        try:
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=self.timeframe,
                limit=max(self.short_period, self.long_period) + 10,
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
            df.set_index("timestamp", inplace=True)

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            self.historical_data = df
            logger.info(f"{self.symbol} için tarihsel veriler güncellendi")

        except Exception as e:
            logger.error(f"Tarihsel veriler güncellenirken hata oluştu: {e}")
            raise

    def generate_signal(self) -> Dict[str, Any]:
        """
        Trading sinyali üretir.

        Returns:
            Dict[str, Any]: Sinyal bilgileri
        """
        if self.historical_data is None or len(self.historical_data) < max(
            self.short_period, self.long_period
        ):
            raise InsufficientDataError(
                f"Yetersiz veri: En az {max(self.short_period, self.long_period)} mum gerekli"
            )

        # SMA hesapla
        short_sma = (
            self.historical_data["close"].rolling(window=self.short_period).mean()
        )
        long_sma = self.historical_data["close"].rolling(window=self.long_period).mean()

        # Güncel fiyatı al
        if self.current_price is None:
            self.current_price = float(self.historical_data["close"].iloc[-1])

        # Sinyal üret
        signal = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "current_price": self.current_price,
            "short_sma": float(short_sma.iloc[-1]),
            "long_sma": float(long_sma.iloc[-1]),
            "action": "HOLD",
            "strength": 0.0,
        }

        # Kesişim kontrolü
        if (
            short_sma.iloc[-2] <= long_sma.iloc[-2]
            and short_sma.iloc[-1] > long_sma.iloc[-1]
        ):
            signal["action"] = "BUY"
            signal["strength"] = (
                short_sma.iloc[-1] - long_sma.iloc[-1]
            ) / long_sma.iloc[-1]
        elif (
            short_sma.iloc[-2] >= long_sma.iloc[-2]
            and short_sma.iloc[-1] < long_sma.iloc[-1]
        ):
            signal["action"] = "SELL"
            signal["strength"] = (
                long_sma.iloc[-1] - short_sma.iloc[-1]
            ) / long_sma.iloc[-1]

        logger.info(f"Sinyal üretildi: {signal}")
        return signal

    def close(self):
        """
        Kaynakları temizler ve WebSocket bağlantısını kapatır.
        """
        self.websocket.unsubscribe_from_price_updates(self.symbol)
        self.websocket.stop()
        logger.info(f"{self.symbol} için SMA stratejisi kapatıldı")

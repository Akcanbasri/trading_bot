"""
Optimized Combined Strategy sınıfı.

Bu sınıf, FiboBULL PA, RSI Middle Band ve MACD göstergelerini
sıralı doğrulama mantığıyla birleştirir.
"""

from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.indicators.fibobuLL_pa import FiboBULLPA
from src.indicators.rsi_middle_band import RSIMiddleBand
from src.indicators.macd import MACD
from src.data.market_data import MarketDataCollector


class OptimizedCombinedStrategy(BaseStrategy):
    """
    Optimize edilmiş birleşik strateji sınıfı.

    FiboBULL PA göstergesi ana tetikleyici olarak kullanılır,
    RSI Middle Band ve MACD göstergeleri doğrulayıcı olarak kullanılır.
    """

    def __init__(
        self,
        data_collector: MarketDataCollector,
        fibo_left_bars: int = 8,
        fibo_right_bars: int = 8,
        rsi_period: int = 14,
        rsi_positive_momentum: int = 50,
        rsi_negative_momentum: int = 45,
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
    ):
        """
        OptimizedCombinedStrategy sınıfını başlatır.

        Args:
            data_collector: Market veri toplayıcı nesnesi
            fibo_left_bars: FiboBULL PA sol bar sayısı
            fibo_right_bars: FiboBULL PA sağ bar sayısı
            rsi_period: RSI periyodu
            rsi_positive_momentum: RSI pozitif momentum seviyesi
            rsi_negative_momentum: RSI negatif momentum seviyesi
            macd_fast_period: MACD hızlı periyot
            macd_slow_period: MACD yavaş periyot
            macd_signal_period: MACD sinyal periyodu
        """
        super().__init__()
        self.data_collector = data_collector

        # Alt stratejileri başlat
        self.fibo_strategy = FiboBULLPA(
            left_bars=fibo_left_bars, right_bars=fibo_right_bars
        )

        self.rsi_strategy = RSIMiddleBand(
            rsi_period=rsi_period,
            positive_momentum=rsi_positive_momentum,
            negative_momentum=rsi_negative_momentum,
        )

        self.macd_strategy = MACD(
            fast_period=macd_fast_period,
            slow_period=macd_slow_period,
            signal_period=macd_signal_period,
        )

        logger.info("OptimizedCombinedStrategy başlatıldı")

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Sıralı doğrulama mantığıyla trading sinyali üretir.

        Args:
            symbol: Trading sembolü
            timeframe: Zaman dilimi

        Returns:
            Dict[str, Any]: Sinyal bilgilerini içeren sözlük
        """
        try:
            # Market verilerini al
            df = self.data_collector.get_historical_data(symbol, timeframe)
            if df.empty:
                logger.warning(f"{symbol} için veri bulunamadı")
                return {"signal": "HOLD", "current_price": None}

            current_price = df["close"].iloc[-1]

            # Alt stratejilerin sinyallerini hesapla
            fibo_result = self.fibo_strategy.calculate(df)
            rsi_result = self.rsi_strategy.calculate(df)
            macd_result = self.macd_strategy.calculate(df)

            # LONG sinyal kontrolü
            long_trigger = (
                fibo_result["long_signal"].iloc[-1] if not fibo_result.empty else False
            )
            rsi_momentum_ok = (
                rsi_result["buy_signal"].iloc[-1] if not rsi_result.empty else False
            )
            macd_hist_ok = (
                macd_result["hist"].iloc[-1] > 0 if not macd_result.empty else False
            )

            if long_trigger and rsi_momentum_ok and macd_hist_ok:
                return {
                    "signal": "LONG",
                    "current_price": current_price,
                    "fibo_triggered": True,
                    "rsi_momentum_ok": True,
                    "macd_hist_ok": True,
                }

            # SHORT sinyal kontrolü
            short_trigger = (
                fibo_result["short_signal"].iloc[-1] if not fibo_result.empty else False
            )
            rsi_momentum_ok = (
                rsi_result["sell_signal"].iloc[-1] if not rsi_result.empty else False
            )
            macd_hist_ok = (
                macd_result["hist"].iloc[-1] < 0 if not macd_result.empty else False
            )

            if short_trigger and rsi_momentum_ok and macd_hist_ok:
                return {
                    "signal": "SHORT",
                    "current_price": current_price,
                    "fibo_triggered": True,
                    "rsi_momentum_ok": True,
                    "macd_hist_ok": True,
                }

            # HOLD sinyali
            return {
                "signal": "HOLD",
                "current_price": current_price,
                "fibo_triggered": False,
                "rsi_momentum_ok": False,
                "macd_hist_ok": False,
            }

        except Exception as e:
            logger.error(f"Sinyal üretilirken hata oluştu: {str(e)}")
            return {"signal": "HOLD", "current_price": None}

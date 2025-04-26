"""
MACD (Moving Average Convergence Divergence) göstergesi.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import talib
from loguru import logger

from src.indicators.base_indicator import BaseIndicator


class MACD(BaseIndicator):
    """
    MACD göstergesi hesaplama sınıfı.

    MACD, trend yönü ve momentum göstergesidir.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = "close",
    ):
        """
        MACD göstergesini başlatır.

        Args:
            fast_period: Hızlı EMA periyodu (varsayılan: 12)
            slow_period: Yavaş EMA periyodu (varsayılan: 26)
            signal_period: Sinyal EMA periyodu (varsayılan: 9)
            column: Hesaplama için kullanılacak veri sütunu (varsayılan: 'close')
        """
        params = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "column": column,
        }
        super().__init__(name="MACD", params=params)

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        MACD değerlerini hesaplar.

        Args:
            data: İşlem verileri DataFrame'i

        Returns:
            pd.DataFrame: MACD değerlerini içeren DataFrame
        """
        if data.empty:
            logger.warning("MACD hesaplaması için veri yok")
            return pd.DataFrame()

        column = self.params["column"]
        if column not in data.columns:
            logger.error(f"{column} sütunu veride bulunamadı")
            return pd.DataFrame()

        try:
            # MACD hesapla
            macd, signal, hist = talib.MACD(
                data[column].values,
                fastperiod=self.params["fast_period"],
                slowperiod=self.params["slow_period"],
                signalperiod=self.params["signal_period"],
            )

            # Sonuçları DataFrame'e dönüştür
            result = pd.DataFrame(
                {"macd": macd, "signal": signal, "hist": hist}, index=data.index
            )

            logger.debug(
                f"MACD başarıyla hesaplandı. Son histogram: {result['hist'].iloc[-1]:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"MACD hesaplanırken hata oluştu: {e}")
            return pd.DataFrame()

    def is_valid_signal(self, data: pd.DataFrame) -> bool:
        """
        MACD değerine göre geçerli bir sinyal olup olmadığını kontrol eder.

        Args:
            data: Kontrol edilecek veri

        Returns:
            bool: Sinyal geçerliyse True, değilse False
        """
        if self.result is None or self.result.empty:
            return False

        last_hist = self.result["hist"].iloc[-1]
        prev_hist = self.result["hist"].iloc[-2]

        # Histogram yön değişimi
        return (last_hist > 0 and prev_hist <= 0) or (last_hist < 0 and prev_hist >= 0)

    def get_signal(self) -> Dict[str, Any]:
        """
        MACD değerine göre alım/satım sinyali üretir.

        Returns:
            Dict: Sinyal bilgisi
        """
        if self.result is None or self.result.empty:
            return {"signal": "NEUTRAL", "strength": 0, "value": None}

        last_hist = self.result["hist"].iloc[-1]
        prev_hist = self.result["hist"].iloc[-2]

        # Sinyal tipi
        if last_hist > 0 and prev_hist <= 0:
            signal = "BUY"
            strength = min(100, abs(last_hist) * 10)  # Histogram değerine göre güç
        elif last_hist < 0 and prev_hist >= 0:
            signal = "SELL"
            strength = min(100, abs(last_hist) * 10)  # Histogram değerine göre güç
        else:
            signal = "NEUTRAL"
            strength = 0

        return {
            "signal": signal,
            "strength": float(strength),
            "value": float(last_hist),
        }

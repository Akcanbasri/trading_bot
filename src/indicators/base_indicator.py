"""
Temel gösterge sınıfı.

Tüm göstergeler için temel sınıf.
"""

from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger


class BaseIndicator:
    """
    Temel gösterge sınıfı.

    Tüm göstergeler bu sınıftan türetilir.
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        """
        Temel gösterge sınıfını başlatır.

        Args:
            name: Gösterge adı
            params: Gösterge parametreleri
        """
        self.name = name
        self.params = params
        self.result = None

        logger.debug(f"{name} göstergesi başlatıldı")

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Gösterge değerlerini hesaplar.

        Args:
            data: İşlem verileri DataFrame'i

        Returns:
            pd.DataFrame: Hesaplama sonuçlarını içeren DataFrame
        """
        raise NotImplementedError("calculate metodu alt sınıflarda uygulanmalıdır")

    def is_valid_signal(self, data: pd.DataFrame) -> bool:
        """
        Geçerli bir sinyal olup olmadığını kontrol eder.

        Args:
            data: Kontrol edilecek veri

        Returns:
            bool: Sinyal geçerliyse True, değilse False
        """
        raise NotImplementedError(
            "is_valid_signal metodu alt sınıflarda uygulanmalıdır"
        )

    def get_signal(self) -> Dict[str, Any]:
        """
        Alım/satım sinyali üretir.

        Returns:
            Dict: Sinyal bilgisi
        """
        raise NotImplementedError("get_signal metodu alt sınıflarda uygulanmalıdır")

    def plot_data(self, ax, data: pd.DataFrame) -> None:
        """
        Gösterge verilerini grafik üzerine çizer.

        Args:
            ax: Matplotlib ekseni
            data: Çizilecek veri
        """
        raise NotImplementedError("plot_data metodu alt sınıflarda uygulanmalıdır")

"""
Temel gösterge (indicator) sınıfı modülü.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np
from loguru import logger


class BaseIndicator(ABC):
    """
    Tüm teknik göstergeler için temel sınıf.
    Yeni göstergeler bu sınıftan türetilmelidir.
    """
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        BaseIndicator sınıfını başlatır.
        
        Args:
            name: Gösterge adı
            params: Gösterge parametreleri
        """
        self.name = name
        self.params = params or {}
        self.result = None
        self.is_ready = False
        logger.debug(f"{name} göstergesi oluşturuldu. Parametreler: {params}")
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Gösterge hesaplaması yapan metot.
        
        Args:
            data: Hesaplama için kullanılacak fiyat verileri
            
        Returns:
            pd.DataFrame: Hesaplama sonuçlarını içeren DataFrame
        """
        pass
    
    def is_valid_signal(self, data: pd.DataFrame) -> bool:
        """
        Gösterge sinyallerinin geçerli olup olmadığını kontrol eder.
        
        Args:
            data: Kontrol edilecek veri
            
        Returns:
            bool: Sinyal geçerliyse True, değilse False
        """
        # Bu metot alt sınıflarda override edilebilir
        return True
    
    def get_last_value(self) -> Union[float, Dict[str, float], None]:
        """
        Göstergenin en son değerini döndürür.
        
        Returns:
            Union[float, Dict[str, float], None]: Göstergenin son değeri veya alt göstergelerin son değerleri
        """
        if self.result is None or self.result.empty:
            return None
        
        try:
            # Tek bir sütun varsa float olarak döndür
            if len(self.result.columns) == 1:
                return self.result.iloc[-1, 0]
            
            # Birden fazla sütun varsa dict olarak döndür
            return self.result.iloc[-1].to_dict()
        except Exception as e:
            logger.error(f"{self.name} için son değer alınamadı: {e}")
            return None
    
    def __str__(self) -> str:
        """
        Göstergenin string temsilini döndürür.
        
        Returns:
            str: Gösterge bilgisi
        """
        param_str = ", ".join([f"{k}={v}" for k, v in self.params.items()])
        return f"{self.name}({param_str})"
    
    def reset(self) -> None:
        """
        Gösterge durumunu sıfırlar.
        """
        self.result = None
        self.is_ready = False
        logger.debug(f"{self.name} göstergesi sıfırlandı")
    
    def update(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Yeni veri geldiğinde göstergeyi günceller.
        
        Args:
            data: Güncelleme için kullanılacak yeni veri
            
        Returns:
            pd.DataFrame: Güncellenen gösterge değerleri
        """
        result = self.calculate(data)
        self.result = result
        self.is_ready = not (result is None or result.empty)
        return result 
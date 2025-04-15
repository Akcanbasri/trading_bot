"""
Temel trading stratejisi için ana sınıf modülü.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from datetime import datetime
from loguru import logger

from src.data.market_data import MarketDataCollector
from src.indicators.base_indicator import BaseIndicator


class BaseStrategy(ABC):
    """
    Tüm ticaret stratejileri için temel sınıf.
    Yeni stratejiler bu sınıftan türetilmelidir.
    """
    
    def __init__(self, name: str, market_data: MarketDataCollector):
        """
        Temel strateji sınıfını başlatır.
        
        Args:
            name: Strateji adı
            market_data: Piyasa verileri toplayıcısı
        """
        self.name = name
        self.market_data = market_data
        self.indicators: Dict[str, BaseIndicator] = {}
        self.data_frames: Dict[str, pd.DataFrame] = {}
        self.params: Dict[str, Any] = {}
        self.last_update_time: Optional[datetime] = None
        
        logger.info(f"{name} stratejisi başlatıldı")
    
    def add_indicator(self, indicator: BaseIndicator) -> None:
        """
        Stratejiye bir gösterge ekler.
        
        Args:
            indicator: Eklenecek gösterge
        """
        self.indicators[indicator.name] = indicator
        logger.debug(f"{self.name} stratejisine {indicator.name} göstergesi eklendi")
    
    def remove_indicator(self, indicator_name: str) -> None:
        """
        Stratejiden bir göstergeyi kaldırır.
        
        Args:
            indicator_name: Kaldırılacak gösterge adı
        """
        if indicator_name in self.indicators:
            del self.indicators[indicator_name]
            logger.debug(f"{self.name} stratejisinden {indicator_name} göstergesi kaldırıldı")
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Strateji parametrelerini ayarlar.
        
        Args:
            params: Strateji parametreleri
        """
        self.params.update(params)
        logger.debug(f"{self.name} stratejisi parametreleri güncellendi: {params}")
    
    def prepare_data(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Strateji için gerekli verileri hazırlar.
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            limit: Alınacak veri sayısı
            
        Returns:
            pd.DataFrame: Hazırlanan veri
        """
        try:
            # Geçmiş verileri al
            data = self.market_data.get_historical_data(
                symbol=symbol,
                interval=timeframe,
                limit=limit
            )
            
            if data.empty:
                logger.warning(f"{symbol} {timeframe} için veri alınamadı")
                return pd.DataFrame()
            
            # Verileri sakla
            key = f"{symbol}_{timeframe}"
            self.data_frames[key] = data
            
            return data
        
        except Exception as e:
            logger.error(f"Strateji için veri hazırlanırken hata: {e}")
            return pd.DataFrame()
    
    def update_data(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Strateji verilerini günceller.
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            limit: Alınacak veri sayısı
            
        Returns:
            pd.DataFrame: Güncellenen veri
        """
        try:
            # Verileri yenile
            data = self.market_data.refresh_data(
                symbol=symbol,
                interval=timeframe,
                limit=limit
            )
            
            if data.empty:
                logger.warning(f"{symbol} {timeframe} için veri güncellenemedi")
                return pd.DataFrame()
            
            # Verileri sakla
            key = f"{symbol}_{timeframe}"
            self.data_frames[key] = data
            self.last_update_time = datetime.now()
            
            return data
        
        except Exception as e:
            logger.error(f"Strateji verileri güncellenirken hata: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Tüm göstergeleri hesaplar.
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Dict[str, pd.DataFrame]: Gösterge sonuçları
        """
        try:
            key = f"{symbol}_{timeframe}"
            
            # Veri yoksa hazırla
            if key not in self.data_frames:
                self.prepare_data(symbol, timeframe)
            
            data = self.data_frames.get(key)
            if data is None or data.empty:
                logger.warning(f"{key} için hesaplama yapılacak veri yok")
                return {}
            
            # Tüm göstergeleri hesapla
            results = {}
            for name, indicator in self.indicators.items():
                result = indicator.calculate(data)
                if not result.empty:
                    results[name] = result
            
            return results
        
        except Exception as e:
            logger.error(f"Göstergeler hesaplanırken hata: {e}")
            return {}
    
    @abstractmethod
    def generate_signal(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Strateji sinyali üretir.
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Dict: Sinyal bilgisi
        """
        pass 
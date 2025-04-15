"""
Piyasa verilerini toplama ve işleme modülü.
"""
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger

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
        logger.info("Market veri toplayıcı başlatıldı")
    
    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
        limit: int = 500,
        use_cache: bool = True
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
                limit=limit
            )
            
            # Boş veri kontrolü
            if not klines:
                logger.warning(f"{symbol} için {interval} verisi bulunamadı")
                return pd.DataFrame()
            
            # DataFrame'e dönüştür
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Veri tiplerini düzenle
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Zaman damgasını indeks olarak ayarla
            df.set_index('timestamp', inplace=True)
            
            # Önbelleğe kaydet
            if use_cache:
                self.data_cache[cache_key] = df
            
            logger.info(f"{symbol} için {interval} verisi alındı. Satır sayısı: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"{symbol} için {interval} verisi alınırken hata: {e}")
            return pd.DataFrame()
    
    def refresh_data(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """
        Önbellekteki veriyi yeniler ve en güncel verileri getirir.
        
        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            interval: Zaman aralığı (örn. "1h", "4h", "1d")
            limit: Alınacak veri sayısı
            
        Returns:
            pd.DataFrame: Güncel veri DataFrame'i
        """
        logger.debug(f"{symbol} {interval} verisi yenileniyor...")
        return self.get_historical_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
            use_cache=False
        )
    
    def get_current_price(self, symbol: str) -> float:
        """
        Bir sembol için güncel fiyatı alır.
        
        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            
        Returns:
            float: Güncel fiyat
        """
        try:
            ticker = self.client.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.debug(f"{symbol} güncel fiyat: {price}")
            return price
        except Exception as e:
            logger.error(f"{symbol} için güncel fiyat alınamadı: {e}")
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
            order_book = self.client.client.get_order_book(symbol=symbol, limit=limit)
            return order_book
        except Exception as e:
            logger.error(f"{symbol} için emir defteri alınamadı: {e}")
            raise 
#!/usr/bin/env python3
"""
Trading Bot ana çalıştırma dosyası
"""
import os
import sys
from pathlib import Path

# Package path'i ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import load_config
from src.utils.logger import setup_logger
from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.signals.signal_processor import SignalProcessor
from src.order_management.order_executor import OrderExecutor
from src.risk_management.risk_manager import RiskManager


def main():
    """Trading bot'un ana çalıştırma fonksiyonu"""
    # Logger kurulumu
    logger = setup_logger()
    logger.info("Trading bot başlatılıyor...")
    
    # Konfigürasyon yükleme
    config = load_config()
    
    try:
        # Binance client oluşturma
        client = BinanceClient(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        
        # Market veri toplayıcı
        data_collector = MarketDataCollector(client)
        
        # Risk yöneticisi
        risk_manager = RiskManager(
            max_open_trades=config.max_open_trades,
            max_risk_percent=config.max_risk_percent
        )
        
        # Emir yöneticisi
        order_executor = OrderExecutor(client, risk_manager)
        
        # Sinyal işleyici
        signal_processor = SignalProcessor(
            data_collector=data_collector,
            strategy_name=config.strategy,
            indicators=config.indicators,
            order_executor=order_executor
        )
        
        # Bot döngüsünü başlat
        signal_processor.start_processing()
        
    except Exception as e:
        logger.error(f"Bot çalışırken hata oluştu: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
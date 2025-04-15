#!/usr/bin/env python3
"""
Trading bot ana modülü.
"""
import os
import time
import logging
import threading
from dotenv import load_dotenv
from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.risk_management.risk_manager import RiskManager
from src.order_management.order_executor import OrderExecutor
from src.signals.signal_processor import SignalProcessor
from src.strategies.combined_strategy import CombinedStrategy
from src.utils.exceptions import InsufficientDataError
from src.utils.logger import setup_logger

# .env dosyasını yükle
load_dotenv()

# Loglama ayarları
logger = setup_logger()

# Global değişkenler
running = True

def signal_processing_loop(signal_processor, symbol, timeframe, check_interval):
    """
    Sinyal işleme döngüsü.
    
    Args:
        signal_processor: Sinyal işleyici
        symbol: Trading sembolü
        timeframe: Zaman dilimi
        check_interval: Kontrol aralığı (saniye)
    """
    global running
    
    logger.info(f"Sinyal işleme döngüsü başlatıldı. Sembol: {symbol}, Zaman dilimi: {timeframe}")
    
    # Set the symbols and timeframes for the signal processor
    signal_processor.set_symbols([symbol])
    signal_processor.set_timeframes([timeframe])
    
    while running:
        try:
            # Process signals
            signals = signal_processor.process_signals()
            
            if signals and symbol in signals and timeframe in signals[symbol]:
                timeframe_signals = signals[symbol][timeframe]
                for strategy_name, signal in timeframe_signals.items():
                    logger.info(f"Yeni sinyal üretildi - Strateji: {strategy_name}, Sinyal: {signal}")
            
            # Belirtilen aralık kadar bekle
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Sinyal işleme döngüsünde hata: {str(e)}")
            time.sleep(check_interval)

def main():
    """
    Trading bot'un ana fonksiyonu.
    """
    global running
    
    try:
        logger.info("Trading bot başlatılıyor...")
        
        # Binance client'ı başlat
        client = BinanceClient(
            api_key=os.getenv("BINANCE_API_KEY"),
            api_secret=os.getenv("BINANCE_API_SECRET"),
            testnet=os.getenv("USE_TESTNET", "True").lower() == "true"
        )
        
        # Market veri toplayıcıyı başlat
        data_collector = MarketDataCollector(client=client)
        logger.info("Market veri toplayıcı başlatıldı")
        
        # Risk yöneticisini başlat
        risk_manager = RiskManager()
        
        # Emir yürütücüyü başlat
        order_executor = OrderExecutor(
            client=client,
            risk_manager=risk_manager
        )
        
        # Birleşik stratejiyi oluştur
        strategy = CombinedStrategy(
            market_data=data_collector,
            fibo_left_bars=int(os.getenv("FIBO_LEFT_BARS", 8)),
            fibo_right_bars=int(os.getenv("FIBO_RIGHT_BARS", 8)),
            rsi_period=int(os.getenv("RSI_PERIOD", 14)),
            rsi_positive_momentum=float(os.getenv("RSI_POSITIVE_MOMENTUM", 70.0)),
            rsi_negative_momentum=float(os.getenv("RSI_NEGATIVE_MOMENTUM", 30.0)),
            rsi_ema_period=int(os.getenv("RSI_EMA_PERIOD", 20)),
            macd_fast_period=int(os.getenv("MACD_FAST_PERIOD", 12)),
            macd_slow_period=int(os.getenv("MACD_SLOW_PERIOD", 26)),
            macd_signal_period=int(os.getenv("MACD_SIGNAL_PERIOD", 9)),
            macd_histogram_threshold=float(os.getenv("MACD_HISTOGRAM_THRESHOLD", 0.0))
        )
        logger.info("Birleşik strateji oluşturuldu")
        
        # Sinyal işleyiciyi başlat
        signal_processor = SignalProcessor(
            data_collector=data_collector,
            order_executor=order_executor,
            strategy_name="combined_strategy",
            indicators=["RSI", "MACD", "FIBOBULL"],
            check_interval=int(os.getenv("CHECK_INTERVAL", "60"))
        )
        
        # Stratejiyi ekle
        signal_processor.add_strategy(strategy)
        
        # Sembolleri ve zaman dilimlerini ayarla
        symbol = os.getenv("TRADING_SYMBOL", "DOGEUSDT")
        timeframe = os.getenv("TRADING_TIMEFRAME", "15m")
        check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
        
        # Sinyal işleme döngüsünü başlat
        signal_thread = threading.Thread(
            target=signal_processing_loop,
            args=(signal_processor, symbol, timeframe, check_interval)
        )
        signal_thread.daemon = True
        signal_thread.start()
        
        logger.info(f"Trading bot çalışıyor. Sembol: {symbol}, Zaman dilimi: {timeframe}")
        logger.info("Botu durdurmak için Ctrl+C tuşlarına basın.")
        
        # Ana döngü
        while running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Kullanıcı tarafından durduruldu.")
                running = False
                break
        
    except InsufficientDataError as e:
        logger.error(f"Yetersiz veri hatası: {str(e)}")
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {str(e)}")
    finally:
        logger.info("Trading bot kapatılıyor...")
        running = False

if __name__ == "__main__":
    main() 
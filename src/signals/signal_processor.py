"""
Ticaret sinyallerini işleme ve karar verme modülü.
"""
from typing import Dict, List, Any, Optional, Union
import time
import threading
from datetime import datetime, timedelta
from loguru import logger

from src.data.market_data import MarketDataCollector
from src.strategies.base_strategy import BaseStrategy
from src.order_management.order_executor import OrderExecutor


class SignalProcessor:
    """
    Farklı stratejilerin ürettiği sinyalleri işleyerek
    ticaret kararları alan sınıf.
    """
    
    def __init__(
        self,
        data_collector: MarketDataCollector,
        order_executor: OrderExecutor,
        strategy_name: str = "moving_average_crossover",
        indicators: List[str] = None,
        check_interval: int = 60  # Saniye cinsinden
    ):
        """
        Signal Processor sınıfını başlatır.
        
        Args:
            data_collector: Piyasa veri toplayıcısı
            order_executor: Emir yürütücüsü
            strategy_name: Kullanılacak strateji adı (varsayılan: "moving_average_crossover")
            indicators: Kullanılacak göstergeler (varsayılan: None)
            check_interval: Kontrol aralığı, saniye cinsinden (varsayılan: 60)
        """
        self.data_collector = data_collector
        self.order_executor = order_executor
        self.strategy_name = strategy_name
        self.indicators = indicators or ["RSI", "MACD"]
        self.check_interval = check_interval
        
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_symbols: List[str] = []
        self.timeframes: List[str] = []
        
        self.is_running = False
        self.processing_thread = None
        
        self.last_signals: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Sinyal işleyicisi başlatıldı. Strateji: {strategy_name}")
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Sinyal işleyiciye bir strateji ekler.
        
        Args:
            strategy: Eklenecek strateji
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"{strategy.name} stratejisi eklendi")
    
    def set_symbols(self, symbols: List[str]) -> None:
        """
        İzlenecek sembolleri ayarlar.
        
        Args:
            symbols: İzlenecek semboller listesi
        """
        self.active_symbols = symbols
        logger.info(f"İzlenecek semboller: {symbols}")
    
    def set_timeframes(self, timeframes: List[str]) -> None:
        """
        İzlenecek zaman dilimlerini ayarlar.
        
        Args:
            timeframes: İzlenecek zaman dilimleri listesi
        """
        self.timeframes = timeframes
        logger.info(f"İzlenecek zaman dilimleri: {timeframes}")
    
    def process_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Tüm stratejilerin, semboller için sinyallerini işler.
        
        Returns:
            Dict[str, Dict[str, Any]]: Sembol başına sinyal bilgisi
        """
        signals = {}
        
        if not self.strategies:
            logger.warning("İşlenecek strateji yok")
            return signals
        
        if not self.active_symbols:
            logger.warning("İzlenecek sembol yok")
            return signals
        
        if not self.timeframes:
            logger.warning("İzlenecek zaman dilimi yok")
            return signals
        
        # Her sembol ve zaman dilimi için stratejileri çalıştır
        for symbol in self.active_symbols:
            symbol_signals = {}
            
            for timeframe in self.timeframes:
                timeframe_signals = {}
                
                for strategy_name, strategy in self.strategies.items():
                    try:
                        signal = strategy.generate_signal(symbol, timeframe)
                        timeframe_signals[strategy_name] = signal
                        
                        logger.debug(f"{symbol} {timeframe} için {strategy_name} "
                                   f"stratejisi sinyali: {signal['signal']} "
                                   f"(Güç: {signal['strength']})")
                    except Exception as e:
                        logger.error(f"{strategy_name} stratejisi sinyal işlenirken hata: {e}")
                
                symbol_signals[timeframe] = timeframe_signals
            
            signals[symbol] = symbol_signals
        
        self.last_signals = signals
        return signals
    
    def make_trading_decisions(self) -> List[Dict[str, Any]]:
        """
        Sinyallere dayanarak ticaret kararları alır.
        
        Returns:
            List[Dict[str, Any]]: Alınan ticaret kararlarının listesi
        """
        decisions = []
        
        if not self.last_signals:
            logger.warning("Karar alınacak sinyal yok")
            return decisions
        
        # Her sembol için sinyalleri değerlendir
        for symbol, timeframes in self.last_signals.items():
            # Birincil zaman dilimine göre değerlendir
            primary_timeframe = self.timeframes[0] if self.timeframes else "1h"
            
            if primary_timeframe not in timeframes:
                continue
            
            # Birincil strateji sinyalini al
            primary_strategy = self.strategy_name
            strategies_data = timeframes[primary_timeframe]
            
            if primary_strategy not in strategies_data:
                continue
            
            primary_signal = strategies_data[primary_strategy]
            
            # Sinyal değerlendirme
            if primary_signal["signal"] == "BUY" and primary_signal["strength"] >= 80:
                # Güçlü ALIM sinyali
                decision = {
                    "action": "BUY",
                    "symbol": symbol,
                    "price": "MARKET",  # Piyasa fiyatından
                    "time": datetime.now().isoformat(),
                    "reason": f"{primary_strategy} stratejisi güçlü alım sinyali",
                    "signal_strength": primary_signal["strength"],
                    "strategy": primary_strategy,
                    "timeframe": primary_timeframe
                }
                decisions.append(decision)
                logger.info(f"ALIM kararı: {symbol} - Güç: {primary_signal['strength']}")
                
            elif primary_signal["signal"] == "SELL" and primary_signal["strength"] >= 80:
                # Güçlü SATIM sinyali
                decision = {
                    "action": "SELL",
                    "symbol": symbol,
                    "price": "MARKET",  # Piyasa fiyatından
                    "time": datetime.now().isoformat(),
                    "reason": f"{primary_strategy} stratejisi güçlü satım sinyali",
                    "signal_strength": primary_signal["strength"],
                    "strategy": primary_strategy,
                    "timeframe": primary_timeframe
                }
                decisions.append(decision)
                logger.info(f"SATIM kararı: {symbol} - Güç: {primary_signal['strength']}")
        
        return decisions
    
    def execute_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        """
        Ticaret kararlarını yürütür.
        
        Args:
            decisions: Yürütülecek kararlar listesi
        """
        for decision in decisions:
            try:
                symbol = decision["symbol"]
                action = decision["action"]
                
                # Kararı yürüt
                if action == "BUY":
                    self.order_executor.create_market_buy_order(
                        symbol=symbol,
                        quantity=None,  # Risk yöneticisi hesaplayacak
                        signal_data=decision
                    )
                elif action == "SELL":
                    self.order_executor.create_market_sell_order(
                        symbol=symbol,
                        quantity=None,  # Risk yöneticisi hesaplayacak
                        signal_data=decision
                    )
                else:
                    logger.warning(f"Bilinmeyen karar tipi: {action}")
                
            except Exception as e:
                logger.error(f"{decision['symbol']} için {decision['action']} kararı yürütülürken hata: {e}")
    
    def processing_loop(self) -> None:
        """
        Sinyal işleme döngüsü.
        """
        logger.info("Sinyal işleme döngüsü başlatıldı")
        
        while self.is_running:
            try:
                # Sinyalleri işle
                signals = self.process_signals()
                
                # Kararları al
                decisions = self.make_trading_decisions()
                
                # Kararları yürüt
                if decisions:
                    self.execute_decisions(decisions)
                
                # Bekleme
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Sinyal işleme döngüsünde hata: {e}")
                time.sleep(self.check_interval)
    
    def start_processing(self) -> None:
        """
        Sinyal işleme sürecini başlatır.
        """
        if self.is_running:
            logger.warning("Sinyal işleme zaten çalışıyor")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self.processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("Sinyal işleme başlatıldı")
    
    def stop_processing(self) -> None:
        """
        Sinyal işleme sürecini durdurur.
        """
        self.is_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        logger.info("Sinyal işleme durduruldu") 
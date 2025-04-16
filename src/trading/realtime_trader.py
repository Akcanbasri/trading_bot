"""
Real-time trading module.

This module provides classes for real-time trading based on strategy signals.
"""
from typing import Dict, List, Any, Optional, Union, Set
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
from uuid import uuid4
import traceback
from loguru import logger
import os

from src.data.market_data import MarketDataCollector
from src.strategies.base_strategy import BaseStrategy
from src.api.client import BinanceClient
from src.backtest.backtest_engine import Trade


class RealTimeTrader:
    """Real-time trading implementation for live or paper trading."""
    
    def __init__(
        self,
        client: BinanceClient,
        market_data: MarketDataCollector,
        strategy: BaseStrategy,
        trading_mode: str = "live",  # Changed default to "live"
        initial_capital: float = 10000.0,
        position_size_type: str = "percentage",
        position_size_value: float = 5.0,
        use_stop_loss: bool = True,
        stop_loss_percentage: float = 2.0,
        use_take_profit: bool = True,
        take_profit_percentage: float = 4.0,
        max_positions: int = 5,
        check_interval_seconds: int = 10
    ):
        """
        Initialize RealTimeTrader.
        
        Args:
            client: Binance API client
            market_data: Market data collector
            strategy: Trading strategy
            trading_mode: "live" or "paper" trading mode
            initial_capital: Initial capital for paper trading
            position_size_type: Position sizing type ("percentage" or "fixed")
            position_size_value: Position size value (percentage or fixed amount)
            use_stop_loss: Whether to use stop loss
            stop_loss_percentage: Stop loss percentage
            use_take_profit: Whether to use take profit
            take_profit_percentage: Take profit percentage
            max_positions: Maximum number of simultaneous positions
            check_interval_seconds: Interval between market checks in seconds
        """
        self.client = client
        self.market_data = market_data
        self.strategy = strategy
        self.trading_mode = trading_mode
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_size_type = position_size_type
        self.position_size_value = position_size_value
        self.use_stop_loss = use_stop_loss
        self.stop_loss_percentage = stop_loss_percentage
        self.use_take_profit = use_take_profit
        self.take_profit_percentage = take_profit_percentage
        self.max_positions = max_positions
        self.check_interval_seconds = check_interval_seconds
        
        # State variables
        self.is_running = False
        self.open_positions: Dict[str, Trade] = {}
        self.all_trades: List[Trade] = []
        self.symbols_watching: Set[str] = set()
        self.last_update_time: Dict[str, datetime] = {}
        self.trader_thread = None
        
        # For live trading, fetch account balance
        if trading_mode == "live":
            try:
                account = self.client.get_account()
                balance = float(next(item for item in account["balances"] if item["asset"] == "USDT")["free"])
                self.initial_capital = balance
                self.current_capital = balance
                logger.info(f"Live trading initialized with {balance} USDT balance")
                
                # Set up futures account if needed
                if os.getenv('USE_FUTURES', 'False').lower() == 'true':
                    self.client.futures_change_leverage(
                        symbol=os.getenv('TRADING_SYMBOL', 'DOGEUSDT'),
                        leverage=int(os.getenv('DEFAULT_LEVERAGE', '5'))
                    )
                    logger.info(f"Futures leverage set to {os.getenv('DEFAULT_LEVERAGE', '5')}x")
            except Exception as e:
                logger.error(f"Failed to fetch account balance: {e}")
                raise
        else:
            logger.info(f"Paper trading initialized with {initial_capital} simulated capital")
    
    def start(self, symbols: List[str], timeframe: str) -> None:
        """
        Start real-time trading.
        
        Args:
            symbols: List of symbols to trade
            timeframe: Timeframe to use for analysis
        """
        if self.is_running:
            logger.warning("Trading is already running")
            return
        
        self.is_running = True
        self.symbols_watching = set(symbols)
        
        # Start trading in a separate thread
        self.trader_thread = threading.Thread(
            target=self._trading_loop,
            args=(symbols, timeframe),
            daemon=True
        )
        self.trader_thread.start()
        
        logger.info(f"Real-time trading started for {len(symbols)} symbols on {timeframe} timeframe")
    
    def stop(self) -> None:
        """Stop real-time trading."""
        if not self.is_running:
            logger.warning("Trading is not running")
            return
        
        self.is_running = False
        
        if self.trader_thread:
            self.trader_thread.join(timeout=10)
        
        logger.info("Real-time trading stopped")
    
    def _trading_loop(self, symbols: List[str], timeframe: str) -> None:
        """
        Main trading loop.
        
        Args:
            symbols: List of symbols to trade
            timeframe: Timeframe to use for analysis
        """
        while self.is_running:
            try:
                self._process_cycle(symbols, timeframe)
                
                # Sleep until next check
                time.sleep(self.check_interval_seconds)
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(10)  # Sleep a bit before retry on error
    
    def _process_cycle(self, symbols: List[str], timeframe: str) -> None:
        """
        Process one trading cycle.
        
        Args:
            symbols: List of symbols to trade
            timeframe: Timeframe to use for analysis
        """
        logger.debug(f"Processing trading cycle for {len(symbols)} symbols")
        
        # Update data for all symbols
        for symbol in symbols:
            try:
                # Update market data
                df = self.market_data.refresh_data(symbol, timeframe)
                if df.empty:
                    logger.warning(f"No data available for {symbol}")
                    continue
                
                self.last_update_time[symbol] = datetime.now()
                
                # First check existing positions
                if symbol in self.open_positions:
                    self._check_position(symbol)
                # Then check for new signals if we have capacity
                elif len(self.open_positions) < self.max_positions:
                    self._check_for_signals(symbol, timeframe)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                logger.error(traceback.format_exc())
    
    def _check_position(self, symbol: str) -> None:
        """
        Mevcut pozisyonu kontrol eder ve gerekirse kapatır.
        
        Args:
            symbol: İşlem sembolü
        """
        try:
            position = self.open_positions.get(symbol)
            if not position:
                return
                
            # Get current price instead of using historical data
            current_price = self.market_data.get_current_price(symbol)
            
            # Calculate profit/loss
            entry_price = position.entry_price
            quantity = position.quantity
            side = position.direction
            
            if side == 'LONG':
                pnl = (current_price - entry_price) * quantity
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl = (entry_price - current_price) * quantity
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                
            logger.info(f"{symbol} pozisyon durumu - Giriş: {entry_price}, Mevcut: {current_price}, PNL: {pnl:.2f} ({pnl_percentage:.2f}%)")
            
            # Check stop loss and take profit
            if pnl_percentage <= -self.stop_loss_percentage:
                logger.info(f"{symbol} stop loss tetiklendi: {pnl_percentage:.2f}%")
                self._close_position(position, current_price)
            elif pnl_percentage >= self.take_profit_percentage:
                logger.info(f"{symbol} take profit tetiklendi: {pnl_percentage:.2f}%")
                self._close_position(position, current_price)
                
        except Exception as e:
            logger.error(f"Pozisyon kontrolü sırasında hata: {e}")
    
    def _check_for_signals(self, symbol: str, timeframe: str) -> None:
        """
        Belirtilen sembol için sinyal kontrolü yapar.
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
        """
        try:
            # Get historical data for strategy
            df = self.market_data.get_historical_data(symbol, timeframe)
            if df is None or df.empty:
                logger.warning(f"{symbol} için veri alınamadı")
                return
                
            # Get current price
            current_price = self.market_data.get_current_price(symbol)
            if current_price is None:
                logger.warning(f"{symbol} için güncel fiyat alınamadı")
                return
                
            # Generate signal
            signal = self.strategy.generate_signal(symbol, df)
            if not signal:
                return
                
            signal_type = signal.get('signal')
            if not signal_type:
                return
                
            # Log signal
            logger.info(f"{symbol} için {signal_type} sinyali alındı - Fiyat: {current_price}")
            
            # Execute trade based on signal
            if signal_type == "BUY":
                self._open_position(symbol, "LONG", current_price)
            elif signal_type == "SELL":
                self._open_position(symbol, "SHORT", current_price)
                
        except Exception as e:
            logger.error(f"Sinyal kontrolü sırasında hata: {e}")
    
    def _open_position(self, symbol: str, direction: str, current_price: float) -> None:
        """
        Yeni pozisyon açar.
        
        Args:
            symbol: İşlem sembolü
            direction: İşlem yönü (LONG/SHORT)
            current_price: Giriş fiyatı
        """
        try:
            # Check if we can open more positions
            if len(self.open_positions) >= self.max_positions:
                logger.warning(f"Maksimum pozisyon sayısına ulaşıldı ({self.max_positions})")
                return
                
            # Calculate position size
            if self.position_size_type == "percentage":
                position_value = self.current_capital * (self.position_size_value / 100)
            else:  # fixed
                position_value = min(self.position_size_value, self.current_capital)
                
            quantity = position_value / current_price
            
            # Calculate stop loss and take profit prices
            if direction == "LONG":
                stop_loss_price = current_price * (1 - (self.stop_loss_percentage / 100)) if self.use_stop_loss else None
                take_profit_price = current_price * (1 + (self.take_profit_percentage / 100)) if self.use_take_profit else None
            else:  # SHORT
                stop_loss_price = current_price * (1 + (self.stop_loss_percentage / 100)) if self.use_stop_loss else None
                take_profit_price = current_price * (1 - (self.take_profit_percentage / 100)) if self.use_take_profit else None
                
            # Create position object
            position = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': current_price,
                'quantity': quantity,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'entry_time': datetime.now()
            }
            
            # Add to open positions
            self.open_positions.append(position)
            
            # Log position
            logger.info(f"Yeni pozisyon açıldı: {symbol} {direction} - Fiyat: {current_price}, "
                       f"Miktar: {quantity:.8f}, Stop Loss: {stop_loss_price}, Take Profit: {take_profit_price}")
                       
        except Exception as e:
            logger.error(f"Pozisyon açma sırasında hata: {e}")
    
    def _close_position(self, position: dict, current_price: float) -> None:
        """
        Pozisyonu kapatır ve kar/zarar hesaplar.
        
        Args:
            position: Kapatılacak pozisyon
            current_price: Çıkış fiyatı
        """
        try:
            # Calculate profit/loss
            if position['direction'] == "LONG":
                pnl = (current_price - position['entry_price']) * position['quantity']
            else:  # SHORT
                pnl = (position['entry_price'] - current_price) * position['quantity']
                
            # Update capital
            self.current_capital += pnl
            
            # Log position close
            logger.info(f"Pozisyon kapatıldı: {position['symbol']} {position['direction']} - "
                       f"Giriş: {position['entry_price']}, Çıkış: {current_price}, "
                       f"Kar/Zarar: {pnl:.2f} USDT")
                       
            # Remove from open positions
            self.open_positions.remove(position)
            
            # Update trade history
            trade = {
                'symbol': position['symbol'],
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'entry_time': position['entry_time'],
                'exit_time': datetime.now()
            }
            self.all_trades.append(trade)
            
        except Exception as e:
            logger.error(f"Pozisyon kapatma sırasında hata: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics based on closed trades.
        
        Returns:
            Dict: Performance metrics
        """
        closed_trades = [t for t in self.all_trades if t.status == "CLOSED"]
        
        if not closed_trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "open_positions": len(self.open_positions),
                "current_capital": self.current_capital
            }
        
        # Count winning and losing trades
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        num_trades = len(closed_trades)
        num_winning = len(winning_trades)
        
        # Calculate win rate
        win_rate = (num_winning / num_trades) * 100 if num_trades > 0 else 0
        
        # Calculate total P&L
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        
        # Calculate max drawdown
        peak = self.initial_capital
        drawdowns = []
        current = self.initial_capital
        
        for trade in closed_trades:
            if trade.pnl:
                current += trade.pnl
                if current > peak:
                    peak = current
                drawdown = ((peak - current) / peak) * 100
                drawdowns.append(drawdown)
        
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        return {
            "total_trades": num_trades,
            "winning_trades": num_winning,
            "losing_trades": num_trades - num_winning,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_pnl_percent": (total_pnl / self.initial_capital) * 100,
            "max_drawdown": max_drawdown,
            "open_positions": len(self.open_positions),
            "current_capital": self.current_capital
        }
    
    def add_symbol(self, symbol: str) -> None:
        """
        Add a symbol to watch for trading signals.
        
        Args:
            symbol: Symbol to add
        """
        self.symbols_watching.add(symbol)
        logger.info(f"Added {symbol} to watchlist")
    
    def remove_symbol(self, symbol: str) -> None:
        """
        Remove a symbol from the watch list.
        
        Args:
            symbol: Symbol to remove
        """
        if symbol in self.symbols_watching:
            self.symbols_watching.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")
            
        # Close position if open
        if symbol in self.open_positions:
            current_price = self.market_data.get_current_price(symbol)
            self._close_position(self.open_positions[symbol], current_price)
    
    def get_trader_status(self) -> Dict[str, Any]:
        """
        Get the current status of the trader.
        
        Returns:
            Dict: Status information
        """
        return {
            "running": self.is_running,
            "mode": self.trading_mode,
            "current_capital": self.current_capital,
            "open_positions": len(self.open_positions),
            "total_trades": len(self.all_trades),
            "closed_trades": len([t for t in self.all_trades if t.status == "CLOSED"]),
            "symbols_watching": list(self.symbols_watching)
        }
    
    def export_trades_to_csv(self, file_path: str) -> None:
        """
        Export trades to CSV file.
        
        Args:
            file_path: Path to save the CSV file
        """
        if not self.all_trades:
            logger.warning("No trades to export")
            return
            
        df = pd.DataFrame([
            {
                'symbol': t.symbol,
                'entry_time': t.entry_time,
                'entry_price': t.entry_price,
                'exit_time': t.exit_time,
                'exit_price': t.exit_price,
                'direction': t.direction,
                'quantity': t.quantity,
                'pnl': t.pnl,
                'pnl_percent': t.pnl_percent,
                'status': t.status,
                'strategy': t.strategy_name,
                'trade_id': t.trade_id
            } for t in self.all_trades
        ])
        
        df.to_csv(file_path, index=False)
        logger.info(f"Trade data exported to {file_path}") 
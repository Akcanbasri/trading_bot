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
        trading_mode: str = "paper",  # "live" or "paper"
        initial_capital: float = 10000.0,  # For paper trading
        position_size_type: str = "percentage",  # "percentage" or "fixed"
        position_size_value: float = 5.0,  # 5% of capital or fixed amount
        use_stop_loss: bool = True,
        stop_loss_percentage: float = 2.0,
        use_take_profit: bool = True,
        take_profit_percentage: float = 4.0,
        max_positions: int = 5,
        check_interval_seconds: int = 60
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
        self.open_positions: Dict[str, Trade] = {}  # Symbol -> Trade
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
                    self._check_position(symbol, df)
                # Then check for new signals if we have capacity
                elif len(self.open_positions) < self.max_positions:
                    self._check_for_signals(symbol, timeframe)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                logger.error(traceback.format_exc())
    
    def _check_position(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Check and update an existing position.
        
        Args:
            symbol: Trading symbol
            data: Latest market data
        """
        if symbol not in self.open_positions:
            return
            
        trade = self.open_positions[symbol]
        current_price = data.iloc[-1]['close']
        
        # Check for stop loss
        if self.use_stop_loss and trade.stop_loss is not None:
            if (trade.direction == "LONG" and current_price <= trade.stop_loss) or \
               (trade.direction == "SHORT" and current_price >= trade.stop_loss):
                self._close_position(symbol, current_price, "stop_loss")
                return
        
        # Check for take profit
        if self.use_take_profit and trade.take_profit is not None:
            if (trade.direction == "LONG" and current_price >= trade.take_profit) or \
               (trade.direction == "SHORT" and current_price <= trade.take_profit):
                self._close_position(symbol, current_price, "take_profit")
                return
        
        # Check for exit signals from strategy
        signal = self.strategy.generate_signal(symbol, data)
        if signal:
            signal_type = signal.get('signal', None)
            
            # If holding LONG and signal is SELL or holding SHORT and signal is BUY
            if (trade.direction == "LONG" and signal_type == "SELL") or \
               (trade.direction == "SHORT" and signal_type == "BUY"):
                self._close_position(symbol, current_price, "signal")
    
    def _check_for_signals(self, symbol: str, timeframe: str) -> None:
        """
        Check for new entry signals.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
        """
        # Check if we can open more positions
        if len(self.open_positions) >= self.max_positions:
            return
            
        # Generate signal
        signal = self.strategy.generate_signal(symbol, timeframe)
        
        if not signal:
            return
            
        signal_type = signal.get('signal', None)
        current_price = self.market_data.get_current_price(symbol)
        
        if signal_type == "BUY":
            # Calculate position size
            if self.position_size_type == "percentage":
                position_value = self.current_capital * (self.position_size_value / 100)
            else:  # fixed
                position_value = min(self.position_size_value, self.current_capital)
                
            quantity = position_value / current_price
            
            # Calculate stop loss and take profit prices
            stop_loss_price = current_price * (1 - (self.stop_loss_percentage / 100)) if self.use_stop_loss else None
            take_profit_price = current_price * (1 + (self.take_profit_percentage / 100)) if self.use_take_profit else None
            
            # Open position
            self._open_position(
                symbol=symbol,
                price=current_price,
                direction="LONG",
                quantity=quantity,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
        
        elif signal_type == "SHORT":
            # Calculate position size
            if self.position_size_type == "percentage":
                position_value = self.current_capital * (self.position_size_value / 100)
            else:  # fixed
                position_value = min(self.position_size_value, self.current_capital)
                
            quantity = position_value / current_price
            
            # Calculate stop loss and take profit prices
            stop_loss_price = current_price * (1 + (self.stop_loss_percentage / 100)) if self.use_stop_loss else None
            take_profit_price = current_price * (1 - (self.take_profit_percentage / 100)) if self.use_take_profit else None
            
            # Open position
            self._open_position(
                symbol=symbol,
                price=current_price,
                direction="SHORT",
                quantity=quantity,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
    
    def _open_position(
        self,
        symbol: str,
        price: float,
        direction: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """
        Open a new position.
        
        Args:
            symbol: Trading symbol
            price: Entry price
            direction: Trade direction ('LONG' or 'SHORT')
            quantity: Trade quantity
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
        """
        trade_id = str(uuid4())
        entry_time = datetime.now()
        
        if self.trading_mode == "live":
            try:
                # Execute order through Binance API
                side = "BUY" if direction == "LONG" else "SELL"
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=quantity
                )
                
                # Get actual execution price and quantity
                price = float(order['fills'][0]['price'])
                actual_quantity = sum(float(fill['qty']) for fill in order['fills'])
                
                # Create stop loss order if needed
                if self.use_stop_loss and stop_loss is not None:
                    stop_side = "SELL" if direction == "LONG" else "BUY"
                    self.client.create_order(
                        symbol=symbol,
                        side=stop_side,
                        type="STOP_LOSS_LIMIT",
                        timeInForce="GTC",
                        quantity=actual_quantity,
                        price=stop_loss * 0.99 if direction == "LONG" else stop_loss * 1.01,  # Buffer for execution
                        stopPrice=stop_loss
                    )
                
                # Create take profit order if needed
                if self.use_take_profit and take_profit is not None:
                    take_profit_side = "SELL" if direction == "LONG" else "BUY"
                    self.client.create_order(
                        symbol=symbol,
                        side=take_profit_side,
                        type="TAKE_PROFIT_LIMIT",
                        timeInForce="GTC",
                        quantity=actual_quantity,
                        price=take_profit * 1.01 if direction == "LONG" else take_profit * 0.99,  # Buffer for execution
                        stopPrice=take_profit
                    )
                
                logger.info(f"Opened {direction} position for {symbol} at {price} ({actual_quantity} units)")
                
            except Exception as e:
                logger.error(f"Failed to open position: {e}")
                return
        else:
            # Paper trading
            actual_quantity = quantity
            logger.info(f"[PAPER] Opened {direction} position for {symbol} at {price} ({actual_quantity} units)")
        
        # Create trade object
        trade = Trade(
            symbol=symbol,
            entry_time=entry_time,
            entry_price=price,
            direction=direction,
            quantity=actual_quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=self.strategy.name,
            trade_id=trade_id,
            status="OPEN"
        )
        
        # Update state
        self.open_positions[symbol] = trade
        self.all_trades.append(trade)
        
        # Decrease available capital (for paper trading)
        if self.trading_mode == "paper":
            self.current_capital -= price * quantity
    
    def _close_position(
        self,
        symbol: str,
        price: float,
        reason: str
    ) -> None:
        """
        Close an existing position.
        
        Args:
            symbol: Trading symbol
            price: Exit price
            reason: Reason for closing
        """
        if symbol not in self.open_positions:
            logger.warning(f"No open position for {symbol} to close")
            return
            
        trade = self.open_positions[symbol]
        exit_time = datetime.now()
        
        if self.trading_mode == "live":
            try:
                # Execute order through Binance API
                side = "SELL" if trade.direction == "LONG" else "BUY"
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=trade.quantity
                )
                
                # Cancel any existing stop-loss or take-profit orders
                open_orders = self.client.get_open_orders(symbol=symbol)
                for order in open_orders:
                    self.client.cancel_order(symbol=symbol, order_id=order['orderId'])
                
                # Get actual execution price
                price = float(order['fills'][0]['price'])
                
                logger.info(f"Closed {trade.direction} position for {symbol} at {price}. Reason: {reason}")
                
            except Exception as e:
                logger.error(f"Failed to close position: {e}")
                return
        else:
            # Paper trading
            logger.info(f"[PAPER] Closed {trade.direction} position for {symbol} at {price}. Reason: {reason}")
        
        # Close the trade
        trade.close(exit_time, price)
        
        # Update capital (for paper trading)
        if self.trading_mode == "paper" and trade.pnl:
            self.current_capital += price * trade.quantity
        
        # Update trade list and remove from open positions
        del self.open_positions[symbol]
    
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
            self._close_position(symbol, current_price, "symbol_removed")
    
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
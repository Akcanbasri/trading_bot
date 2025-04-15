"""
Backtest engine module for testing trading strategies.

This module provides classes for backtesting trading strategies
and evaluating performance metrics.
"""
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from loguru import logger
from dataclasses import dataclass
from decimal import Decimal

from src.data.market_data import MarketDataCollector
from src.strategies.base_strategy import BaseStrategy
from src.api.client import BinanceClient


@dataclass
class Trade:
    """Class representing a trade during backtesting or live trading."""
    symbol: str
    entry_time: datetime
    entry_price: float
    direction: str  # 'LONG' or 'SHORT'
    quantity: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str = "OPEN"  # 'OPEN' or 'CLOSED'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""
    trade_id: Optional[str] = None
    
    def close(self, exit_time: datetime, exit_price: float) -> None:
        """
        Close a trade.
        
        Args:
            exit_time: Trade exit time
            exit_price: Trade exit price
        """
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = "CLOSED"
        
        # Calculate profit/loss
        if self.direction == "LONG":
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_percent = ((exit_price / self.entry_price) - 1) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_percent = ((self.entry_price / exit_price) - 1) * 100


class BacktestPerformance:
    """Class for calculating and displaying performance metrics for a backtest."""
    
    def __init__(self, trades: List[Trade], initial_capital: float):
        """
        Initialize BacktestPerformance.
        
        Args:
            trades: List of trades from the backtest
            initial_capital: Initial capital amount
        """
        self.trades = trades
        self.initial_capital = initial_capital
        self.capital_history = []
        self.metrics = {}
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics based on the trades.
        
        Returns:
            Dict: Performance metrics
        """
        if not self.trades:
            logger.warning("No trades to calculate metrics")
            return {}
            
        # Ensure all trades are closed
        closed_trades = [t for t in self.trades if t.status == "CLOSED"]
        if len(closed_trades) != len(self.trades):
            logger.warning(f"{len(self.trades) - len(closed_trades)} trades are still open")
        
        # Calculate basic metrics
        num_trades = len(closed_trades)
        profitable_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl <= 0]
        
        num_winning = len(profitable_trades)
        num_losing = len(losing_trades)
        
        win_rate = (num_winning / num_trades) * 100 if num_trades > 0 else 0
        
        if num_winning > 0:
            avg_profit = sum(t.pnl for t in profitable_trades if t.pnl) / num_winning
            avg_profit_percent = sum(t.pnl_percent for t in profitable_trades if t.pnl_percent) / num_winning
        else:
            avg_profit = 0
            avg_profit_percent = 0
            
        if num_losing > 0:
            avg_loss = sum(t.pnl for t in losing_trades if t.pnl) / num_losing
            avg_loss_percent = sum(t.pnl_percent for t in losing_trades if t.pnl_percent) / num_losing
        else:
            avg_loss = 0
            avg_loss_percent = 0
        
        profit_factor = abs(sum(t.pnl for t in profitable_trades if t.pnl) / sum(t.pnl for t in losing_trades if t.pnl)) if sum(t.pnl for t in losing_trades if t.pnl) != 0 else float('inf')
        
        # Calculate equity curve and drawdown
        capital = self.initial_capital
        capital_history = [capital]
        peak_capital = capital
        drawdowns = []
        
        for trade in closed_trades:
            if trade.pnl:
                capital += trade.pnl
                capital_history.append(capital)
                
                if capital > peak_capital:
                    peak_capital = capital
                
                drawdown_percent = ((peak_capital - capital) / peak_capital) * 100
                drawdowns.append(drawdown_percent)
        
        self.capital_history = capital_history
        
        # Calculate maximum drawdown
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Calculate total return
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        total_return = (total_pnl / self.initial_capital) * 100
        
        # Save metrics
        self.metrics = {
            "total_trades": num_trades,
            "winning_trades": num_winning,
            "losing_trades": num_losing,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_profit_percent": avg_profit_percent,
            "avg_loss": avg_loss,
            "avg_loss_percent": avg_loss_percent,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "total_pnl": total_pnl,
            "total_return": total_return,
            "final_capital": capital
        }
        
        return self.metrics
    
    def plot_equity_curve(self, save_path: Optional[str] = None) -> None:
        """
        Plot equity curve.
        
        Args:
            save_path: Path to save the plot image (optional)
        """
        if not self.capital_history:
            logger.warning("No capital history to plot")
            return
            
        plt.figure(figsize=(12, 6))
        plt.plot(self.capital_history, linewidth=2)
        plt.title('Equity Curve')
        plt.xlabel('Trades')
        plt.ylabel('Capital')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
    
    def print_summary(self) -> None:
        """Print a summary of the backtest performance."""
        if not self.metrics:
            self.calculate_metrics()
        
        print("\n========== BACKTEST SUMMARY ==========")
        print(f"Total Trades: {self.metrics['total_trades']}")
        print(f"Winning Trades: {self.metrics['winning_trades']} ({self.metrics['win_rate']:.2f}%)")
        print(f"Losing Trades: {self.metrics['losing_trades']}")
        print(f"Profit Factor: {self.metrics['profit_factor']:.2f}")
        print(f"Average Profit: {self.metrics['avg_profit']:.2f} ({self.metrics['avg_profit_percent']:.2f}%)")
        print(f"Average Loss: {self.metrics['avg_loss']:.2f} ({self.metrics['avg_loss_percent']:.2f}%)")
        print(f"Maximum Drawdown: {self.metrics['max_drawdown']:.2f}%")
        print(f"Total Return: {self.metrics['total_return']:.2f}%")
        print(f"Initial Capital: {self.initial_capital:.2f}")
        print(f"Final Capital: {self.metrics['final_capital']:.2f}")
        print("========================================\n")

    def export_to_csv(self, file_path: str) -> None:
        """
        Export trades to CSV file.
        
        Args:
            file_path: Path to save the CSV file
        """
        if not self.trades:
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
                'strategy': t.strategy_name
            } for t in self.trades
        ])
        
        df.to_csv(file_path, index=False)
        logger.info(f"Trade data exported to {file_path}")


class BacktestEngine:
    """Backtest engine for testing trading strategies with historical data."""
    
    def __init__(
        self,
        client: BinanceClient,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001  # 0.1% default Binance fee
    ):
        """
        Initialize BacktestEngine.
        
        Args:
            client: Binance client for fetching data
            initial_capital: Initial capital for backtest
            commission_rate: Trading commission rate (default: 0.001 = 0.1%)
        """
        self.client = client
        self.market_data = MarketDataCollector(client)
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        self.trades: List[Trade] = []
        self.open_positions: Dict[str, Trade] = {}  # Symbol -> Trade
        self.equity_curve: List[float] = [initial_capital]
        self.performance = None
        
        logger.info(f"Backtest engine initialized with {initial_capital} capital")
    
    def run_backtest(
        self,
        strategy: BaseStrategy,
        symbols: List[str],
        timeframe: str,
        start_date: str,
        end_date: str,
        position_size_type: str = "percentage",  # 'percentage', 'fixed'
        position_size_value: float = 10.0,  # 10% of capital or fixed amount
        use_stop_loss: bool = True,
        stop_loss_percentage: float = 2.0,
        use_take_profit: bool = True,
        take_profit_percentage: float = 4.0
    ) -> BacktestPerformance:
        """
        Run backtest for the given strategy.
        
        Args:
            strategy: Trading strategy to test
            symbols: List of symbols to trade
            timeframe: Timeframe to use
            start_date: Start date for backtest
            end_date: End date for backtest
            position_size_type: Type of position sizing ('percentage' or 'fixed')
            position_size_value: Position size value (percentage or fixed amount)
            use_stop_loss: Whether to use stop loss
            stop_loss_percentage: Stop loss percentage
            use_take_profit: Whether to use take profit
            take_profit_percentage: Take profit percentage
            
        Returns:
            BacktestPerformance: Performance metrics
        """
        logger.info(f"Starting backtest for {strategy.name} on {symbols} from {start_date} to {end_date}")
        
        # Dictionary to store data for each symbol
        data_dict = {}
        
        # Get historical data for each symbol
        for symbol in symbols:
            df = self.market_data.get_historical_data(
                symbol=symbol,
                interval=timeframe,
                start_str=start_date,
                end_str=end_date,
                limit=1000,
                use_cache=False
            )
            
            if df.empty:
                logger.warning(f"No data available for {symbol}, removing from backtest")
                continue
                
            data_dict[symbol] = df
            
        if not data_dict:
            logger.error("No data available for any symbol, cannot run backtest")
            return BacktestPerformance([], self.initial_capital)
            
        # Resample all dataframes to ensure same timestamps
        # This ensures we process all symbols at the same points in time
        # Find the common time range
        min_dates = []
        max_dates = []
        for df in data_dict.values():
            min_dates.append(df.index.min())
            max_dates.append(df.index.max())
        
        min_date = max(min_dates)
        max_date = min(max_dates)
        
        # Filter all dataframes to the common time range
        for symbol in data_dict:
            df = data_dict[symbol]
            df = df[(df.index >= min_date) & (df.index <= max_date)]
            data_dict[symbol] = df
            
        # Get the common index (timestamps)
        common_index = data_dict[list(data_dict.keys())[0]].index
        
        # Initialize tracking variables
        self.current_capital = self.initial_capital
        self.trades = []
        self.open_positions = {}
        self.equity_curve = [self.initial_capital]
        
        # Run through each timestamp
        for timestamp in common_index:
            # Process open positions first (for stop loss/take profit)
            for symbol in list(self.open_positions.keys()):
                if symbol in data_dict:
                    trade = self.open_positions[symbol]
                    current_price = data_dict[symbol].loc[timestamp, 'close']
                    
                    # Check stop loss
                    if use_stop_loss and trade.stop_loss is not None:
                        if (trade.direction == "LONG" and current_price <= trade.stop_loss) or \
                           (trade.direction == "SHORT" and current_price >= trade.stop_loss):
                            self._close_position(symbol, timestamp, current_price, "stop_loss")
                    
                    # Check take profit
                    if use_take_profit and trade.take_profit is not None:
                        if (trade.direction == "LONG" and current_price >= trade.take_profit) or \
                           (trade.direction == "SHORT" and current_price <= trade.take_profit):
                            self._close_position(symbol, timestamp, current_price, "take_profit")
            
            # Update strategy with current data
            for symbol in data_dict:
                # Prepare data slice up to current timestamp
                current_data = data_dict[symbol][data_dict[symbol].index <= timestamp].copy()
                symbol_key = f"{symbol}_{timeframe}"
                strategy.data_frames[symbol_key] = current_data
            
            # Generate signals
            for symbol in data_dict:
                # Skip if already in position for this symbol
                if symbol in self.open_positions:
                    continue
                    
                # Get latest price
                current_price = data_dict[symbol].loc[timestamp, 'close']
                
                # Generate signal
                signal = strategy.generate_signal(symbol, timeframe)
                
                if signal:
                    signal_type = signal.get('signal', None)
                    
                    if signal_type == "BUY":
                        # Calculate position size
                        if position_size_type == "percentage":
                            position_value = self.current_capital * (position_size_value / 100)
                        else:  # fixed
                            position_value = min(position_size_value, self.current_capital)
                            
                        quantity = position_value / current_price
                        
                        # Calculate stop loss and take profit prices
                        stop_loss_price = current_price * (1 - (stop_loss_percentage / 100)) if use_stop_loss else None
                        take_profit_price = current_price * (1 + (take_profit_percentage / 100)) if use_take_profit else None
                        
                        # Open long position
                        self._open_position(
                            symbol=symbol,
                            timestamp=timestamp,
                            price=current_price,
                            direction="LONG",
                            quantity=quantity,
                            stop_loss=stop_loss_price,
                            take_profit=take_profit_price,
                            strategy_name=strategy.name
                        )
                    
                    elif signal_type == "SELL" and symbol in self.open_positions:
                        # Close existing position
                        self._close_position(symbol, timestamp, current_price, "signal")
                        
                    elif signal_type == "SHORT":
                        # Calculate position size
                        if position_size_type == "percentage":
                            position_value = self.current_capital * (position_size_value / 100)
                        else:  # fixed
                            position_value = min(position_size_value, self.current_capital)
                            
                        quantity = position_value / current_price
                        
                        # Calculate stop loss and take profit prices
                        stop_loss_price = current_price * (1 + (stop_loss_percentage / 100)) if use_stop_loss else None
                        take_profit_price = current_price * (1 - (take_profit_percentage / 100)) if use_take_profit else None
                        
                        # Open short position
                        self._open_position(
                            symbol=symbol,
                            timestamp=timestamp,
                            price=current_price,
                            direction="SHORT",
                            quantity=quantity,
                            stop_loss=stop_loss_price,
                            take_profit=take_profit_price,
                            strategy_name=strategy.name
                        )
            
            # Record equity at this timestamp
            self.equity_curve.append(self.current_capital)
        
        # Close any remaining open positions at the end of the backtest
        for symbol in list(self.open_positions.keys()):
            if symbol in data_dict:
                last_price = data_dict[symbol].iloc[-1]['close']
                self._close_position(symbol, common_index[-1], last_price, "end_of_backtest")
        
        # Calculate performance metrics
        self.performance = BacktestPerformance(self.trades, self.initial_capital)
        self.performance.calculate_metrics()
        
        logger.info(f"Backtest completed. Total trades: {len(self.trades)}")
        
        return self.performance
    
    def _open_position(
        self,
        symbol: str,
        timestamp: datetime,
        price: float,
        direction: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy_name: str = ""
    ) -> None:
        """
        Open a new position.
        
        Args:
            symbol: Trading symbol
            timestamp: Entry timestamp
            price: Entry price
            direction: Trade direction ('LONG' or 'SHORT')
            quantity: Trade quantity
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            strategy_name: Name of the strategy
        """
        # Apply commission
        actual_quantity = quantity * (1 - self.commission_rate)
        
        # Create trade object
        trade = Trade(
            symbol=symbol,
            entry_time=timestamp,
            entry_price=price,
            direction=direction,
            quantity=actual_quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=strategy_name,
            trade_id=f"{symbol}_{timestamp.strftime('%Y%m%d%H%M%S')}"
        )
        
        # Add to open positions
        self.open_positions[symbol] = trade
        
        # Add to trades list
        self.trades.append(trade)
        
        logger.debug(f"Opened {direction} position for {symbol} at {price} ({actual_quantity} units)")
    
    def _close_position(
        self,
        symbol: str,
        timestamp: datetime,
        price: float,
        reason: str
    ) -> None:
        """
        Close an existing position.
        
        Args:
            symbol: Trading symbol
            timestamp: Exit timestamp
            price: Exit price
            reason: Reason for closing position
        """
        if symbol not in self.open_positions:
            logger.warning(f"No open position for {symbol} to close")
            return
            
        trade = self.open_positions[symbol]
        
        # Apply commission
        exit_price = price * (1 - self.commission_rate) if trade.direction == "LONG" else price * (1 + self.commission_rate)
        
        # Close the trade
        trade.close(timestamp, exit_price)
        
        # Calculate PnL and update capital
        if trade.pnl:
            self.current_capital += trade.pnl
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        logger.debug(f"Closed {trade.direction} position for {symbol} at {price}. Reason: {reason}, PnL: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)") 
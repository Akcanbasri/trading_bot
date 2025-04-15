"""
Command-line interface for backtest and real-time trading.

This script provides a command-line interface to run backtest or real-time trading
with different strategies and parameters.
"""
import sys
import os
import argparse
import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from src.strategies.fibobuLL_strategy import FiboBuLLStrategy
from src.backtest import BacktestEngine
from src.trading.realtime_trader import RealTimeTrader
from src.config.settings import Settings


def get_strategy(strategy_name, market_data):
    """
    Get a strategy instance by name.
    
    Args:
        strategy_name: Name of the strategy
        market_data: Market data collector instance
        
    Returns:
        BaseStrategy: Strategy instance
    """
    if strategy_name.lower() == "ma_crossover":
        return MovingAverageCrossoverStrategy(market_data)
    elif strategy_name.lower() == "fibobull":
        return FiboBuLLStrategy(market_data)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


def run_backtest(args):
    """
    Run backtest with specified parameters.
    
    Args:
        args: Command-line arguments
    """
    # Load settings
    settings = Settings()
    
    # Initialize Binance client
    client = BinanceClient(
        api_key=settings.get("API.binance.api_key", ""),
        api_secret=settings.get("API.binance.api_secret", ""),
        testnet=settings.get("API.binance.testnet", True)
    )
    
    # Initialize market data collector
    market_data = MarketDataCollector(client)
    
    # Get strategy
    strategy = get_strategy(args.strategy, market_data)
    
    # Set strategy parameters if provided
    if args.strategy_params:
        try:
            params = json.loads(args.strategy_params)
            strategy.set_params(params)
            logger.info(f"Applied strategy parameters: {params}")
        except json.JSONDecodeError:
            logger.error(f"Invalid strategy parameters: {args.strategy_params}")
            return
    
    # Initialize backtest engine
    backtest_engine = BacktestEngine(
        client=client,
        initial_capital=args.capital,
        commission_rate=args.commission
    )
    
    # Parse symbols
    symbols = args.symbols.split(',')
    
    # Calculate date range if not provided
    if not args.start_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        start_date_str = start_date.strftime("%d %b, %Y")
        end_date_str = end_date.strftime("%d %b, %Y")
    else:
        start_date_str = args.start_date
        end_date_str = args.end_date if args.end_date else datetime.now().strftime("%d %b, %Y")
    
    # Run backtest
    print(f"Running backtest for {len(symbols)} symbols from {start_date_str} to {end_date_str}...")
    
    performance = backtest_engine.run_backtest(
        strategy=strategy,
        symbols=symbols,
        timeframe=args.timeframe,
        start_date=start_date_str,
        end_date=end_date_str,
        position_size_type=args.size_type,
        position_size_value=args.size_value,
        use_stop_loss=not args.no_stop_loss,
        stop_loss_percentage=args.stop_loss,
        use_take_profit=not args.no_take_profit,
        take_profit_percentage=args.take_profit
    )
    
    # Print performance summary
    performance.print_summary()
    
    # Plot equity curve
    if not args.no_plot:
        performance.plot_equity_curve()
    
    # Export trades to CSV
    if args.output:
        csv_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = Path(project_root) / "data" / f"backtest_{args.strategy}_{timestamp}.csv"
    
    os.makedirs(csv_path.parent, exist_ok=True)
    performance.export_to_csv(str(csv_path))
    
    print(f"Backtest results exported to {csv_path}")


def run_trading(args):
    """
    Run real-time trading with specified parameters.
    
    Args:
        args: Command-line arguments
    """
    # Load settings
    settings = Settings()
    
    # Initialize Binance client
    client = BinanceClient(
        api_key=settings.get("API.binance.api_key", ""),
        api_secret=settings.get("API.binance.api_secret", ""),
        testnet=settings.get("API.binance.testnet", True)
    )
    
    # Initialize market data collector
    market_data = MarketDataCollector(client)
    
    # Get strategy
    strategy = get_strategy(args.strategy, market_data)
    
    # Set strategy parameters if provided
    if args.strategy_params:
        try:
            params = json.loads(args.strategy_params)
            strategy.set_params(params)
            logger.info(f"Applied strategy parameters: {params}")
        except json.JSONDecodeError:
            logger.error(f"Invalid strategy parameters: {args.strategy_params}")
            return
    
    # Parse symbols
    symbols = args.symbols.split(',')
    
    # Initialize real-time trader
    trader = RealTimeTrader(
        client=client,
        market_data=market_data,
        strategy=strategy,
        trading_mode=args.mode,
        initial_capital=args.capital,
        position_size_type=args.size_type,
        position_size_value=args.size_value,
        use_stop_loss=not args.no_stop_loss,
        stop_loss_percentage=args.stop_loss,
        use_take_profit=not args.no_take_profit,
        take_profit_percentage=args.take_profit,
        max_positions=args.max_positions,
        check_interval_seconds=args.check_interval
    )
    
    # Start trading
    print(f"Starting {args.mode} trading for {len(symbols)} symbols on {args.timeframe} timeframe...")
    trader.start(symbols, args.timeframe)
    
    # Enter main loop
    try:
        while True:
            status = trader.get_trader_status()
            metrics = trader.get_performance_metrics()
            
            print("\n" + "="*50)
            print(f"Trading Status (Mode: {status['mode']})")
            print(f"Current Capital: ${status['current_capital']:.2f}")
            print(f"Open Positions: {status['open_positions']}")
            print(f"Total Trades: {status['total_trades']}")
            print(f"Closed Trades: {status['closed_trades']}")
            
            if metrics['total_trades'] > 0:
                print(f"Win Rate: {metrics['win_rate']:.2f}%")
                print(f"Total P&L: ${metrics['total_pnl']:.2f} ({metrics['total_pnl_percent']:.2f}%)")
                print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
            
            print("="*50)
            
            # Prompt for command
            cmd = input("\nEnter command (status/stop/help): ")
            
            if cmd.lower() == "status":
                # Already displayed status, continue
                pass
            elif cmd.lower() == "stop":
                print("Stopping trading...")
                trader.stop()
                
                # Export trades to CSV
                if args.output:
                    csv_path = args.output
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    csv_path = Path(project_root) / "data" / f"trading_{args.strategy}_{timestamp}.csv"
                
                os.makedirs(csv_path.parent, exist_ok=True)
                trader.export_trades_to_csv(str(csv_path))
                
                print(f"Trading results exported to {csv_path}")
                break
            elif cmd.lower() == "help":
                print("Available commands:")
                print("  status - Display current trading status")
                print("  stop   - Stop trading and exit")
                print("  help   - Display this help message")
            else:
                print("Unknown command. Type 'help' for available commands.")
    
    except KeyboardInterrupt:
        # Handle Ctrl+C
        print("\nStopping trading...")
        trader.stop()
        
        # Export trades to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = Path(project_root) / "data" / f"trading_{args.strategy}_{timestamp}.csv"
        os.makedirs(csv_path.parent, exist_ok=True)
        trader.export_trades_to_csv(str(csv_path))
        
        print(f"Trading results exported to {csv_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Trading Bot CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backtest command
    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument("--strategy", required=True, help="Strategy to use (ma_crossover, fibobull)")
    backtest_parser.add_argument("--strategy-params", help="Strategy parameters as JSON string")
    backtest_parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols to trade")
    backtest_parser.add_argument("--timeframe", default="1h", help="Timeframe to use (e.g., 1m, 5m, 15m, 1h, 4h, 1d)")
    backtest_parser.add_argument("--start-date", help="Start date for backtest (format: '1 Jan, 2023')")
    backtest_parser.add_argument("--end-date", help="End date for backtest (format: '1 Jan, 2023')")
    backtest_parser.add_argument("--days", type=int, default=90, help="Number of days to backtest (if start-date not provided)")
    backtest_parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    backtest_parser.add_argument("--commission", type=float, default=0.001, help="Commission rate")
    backtest_parser.add_argument("--size-type", choices=["percentage", "fixed"], default="percentage", help="Position size type")
    backtest_parser.add_argument("--size-value", type=float, default=10.0, help="Position size value (percentage or fixed amount)")
    backtest_parser.add_argument("--no-stop-loss", action="store_true", help="Disable stop loss")
    backtest_parser.add_argument("--stop-loss", type=float, default=2.0, help="Stop loss percentage")
    backtest_parser.add_argument("--no-take-profit", action="store_true", help="Disable take profit")
    backtest_parser.add_argument("--take-profit", type=float, default=4.0, help="Take profit percentage")
    backtest_parser.add_argument("--no-plot", action="store_true", help="Disable equity curve plotting")
    backtest_parser.add_argument("--output", help="Output CSV file path")
    backtest_parser.set_defaults(func=run_backtest)
    
    # Trading command
    trading_parser = subparsers.add_parser("trading", help="Run real-time trading")
    trading_parser.add_argument("--strategy", required=True, help="Strategy to use (ma_crossover, fibobull)")
    trading_parser.add_argument("--strategy-params", help="Strategy parameters as JSON string")
    trading_parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols to trade")
    trading_parser.add_argument("--timeframe", default="1h", help="Timeframe to use (e.g., 1m, 5m, 15m, 1h, 4h, 1d)")
    trading_parser.add_argument("--mode", choices=["paper", "live"], default="paper", help="Trading mode")
    trading_parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital (for paper trading)")
    trading_parser.add_argument("--size-type", choices=["percentage", "fixed"], default="percentage", help="Position size type")
    trading_parser.add_argument("--size-value", type=float, default=5.0, help="Position size value (percentage or fixed amount)")
    trading_parser.add_argument("--no-stop-loss", action="store_true", help="Disable stop loss")
    trading_parser.add_argument("--stop-loss", type=float, default=2.0, help="Stop loss percentage")
    trading_parser.add_argument("--no-take-profit", action="store_true", help="Disable take profit")
    trading_parser.add_argument("--take-profit", type=float, default=4.0, help="Take profit percentage")
    trading_parser.add_argument("--max-positions", type=int, default=3, help="Maximum number of simultaneous positions")
    trading_parser.add_argument("--check-interval", type=int, default=60, help="Interval between market checks in seconds")
    trading_parser.add_argument("--output", help="Output CSV file path")
    trading_parser.set_defaults(func=run_trading)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        Path(project_root) / "logs" / f"{args.command}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        rotation="50 MB",
        level="DEBUG"
    )
    
    # Run the command
    args.func(args)


if __name__ == "__main__":
    main() 
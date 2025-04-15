"""
Example script demonstrating the backtest module.

This script shows how to use the BacktestEngine to backtest a trading strategy
and evaluate its performance.
"""
import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from loguru import logger

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from src.backtest import BacktestEngine, BacktestPerformance
from src.config.settings import Settings


def run_backtest():
    """Run a backtest of the MovingAverageCrossover strategy."""
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
    
    # Setup strategy
    strategy = MovingAverageCrossoverStrategy(market_data)
    strategy.set_params({
        "fast_ma_period": 9,
        "slow_ma_period": 21
    })
    
    # Initialize backtest engine
    backtest_engine = BacktestEngine(
        client=client,
        initial_capital=10000.0,
        commission_rate=0.001  # 0.1% commission
    )
    
    # Define backtest parameters
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    
    # Calculate date range (last 3 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    start_date_str = start_date.strftime("%d %b, %Y")
    end_date_str = end_date.strftime("%d %b, %Y")
    
    # Run backtest
    print(f"Running backtest for {len(symbols)} symbols from {start_date_str} to {end_date_str}...")
    
    performance = backtest_engine.run_backtest(
        strategy=strategy,
        symbols=symbols,
        timeframe=timeframe,
        start_date=start_date_str,
        end_date=end_date_str,
        position_size_type="percentage",
        position_size_value=10.0,  # 10% of capital per position
        use_stop_loss=True,
        stop_loss_percentage=2.0,
        use_take_profit=True,
        take_profit_percentage=4.0
    )
    
    # Print performance summary
    performance.print_summary()
    
    # Plot equity curve
    performance.plot_equity_curve()
    
    # Export trades to CSV
    csv_path = Path(project_root) / "data" / "backtest_results.csv"
    os.makedirs(csv_path.parent, exist_ok=True)
    performance.export_to_csv(str(csv_path))
    
    print(f"Backtest results exported to {csv_path}")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        Path(project_root) / "logs" / "backtest_{time}.log",
        rotation="50 MB",
        level="DEBUG"
    )
    
    # Run backtest
    run_backtest() 
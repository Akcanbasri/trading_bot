"""
Example script demonstrating the real-time trading module.

This script shows how to use the RealTimeTrader to trade with a strategy
in paper or live mode.
"""
import sys
import os
import time
import signal
from pathlib import Path
import pandas as pd
from datetime import datetime
from loguru import logger

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from src.trading.realtime_trader import RealTimeTrader
from src.config.settings import Settings


def run_live_trading():
    """Run real-time trading using the MovingAverageCrossover strategy."""
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
    
    # Define trading parameters
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    
    # Initialize real-time trader (paper trading mode)
    trader = RealTimeTrader(
        client=client,
        market_data=market_data,
        strategy=strategy,
        trading_mode="paper",  # Change to "live" for real trading
        initial_capital=10000.0,
        position_size_type="percentage",
        position_size_value=5.0,  # 5% of capital per position
        use_stop_loss=True,
        stop_loss_percentage=2.0,
        use_take_profit=True,
        take_profit_percentage=4.0,
        max_positions=3,
        check_interval_seconds=60
    )
    
    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        print("\nStopping trading...")
        trader.stop()
        
        # Export trades to CSV
        csv_path = Path(project_root) / "data" / "trading_results.csv"
        os.makedirs(csv_path.parent, exist_ok=True)
        trader.export_trades_to_csv(str(csv_path))
        
        print(f"Trading results exported to {csv_path}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start trading
    print(f"Starting real-time trading for {len(symbols)} symbols on {timeframe} timeframe...")
    trader.start(symbols, timeframe)
    
    # Main loop for status updates
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
            
            # Wait for next status update
            time.sleep(300)  # Update every 5 minutes
            
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        Path(project_root) / "logs" / "trading_{time}.log",
        rotation="50 MB",
        level="DEBUG"
    )
    
    # Run real-time trading
    run_live_trading() 
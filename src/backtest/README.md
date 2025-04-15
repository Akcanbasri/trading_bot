# Backtest and Real-time Trading Modules

This package provides comprehensive backtest and real-time trading functionality for trading strategies on the Binance exchange.

## Features

- **Backtest Engine**: Test trading strategies with historical data
- **Real-time Trading**: Execute trading strategies in paper or live mode
- **Performance Metrics**: Calculate and visualize key performance indicators
- **Flexible Configuration**: Customize position sizing, risk management, and more
- **CLI Interface**: Run backtests and live trading from the command line

## Modules

### BacktestEngine

The `BacktestEngine` class allows you to test trading strategies with historical data from Binance.

Features:
- Run backtests across multiple symbols simultaneously
- Configure position sizing (percentage or fixed)
- Enable stop-loss and take-profit mechanisms
- Calculate comprehensive performance metrics

### RealTimeTrader

The `RealTimeTrader` class allows you to run trading strategies in real-time with paper or live trading.

Features:
- Paper trading mode for risk-free testing
- Live trading mode for execution on Binance
- Concurrent trading on multiple symbols
- Real-time performance monitoring

### Trade and BacktestPerformance

Supporting classes for tracking trades and calculating performance metrics:
- Win rate, profit factor, and total return
- Maximum drawdown calculation
- Equity curve visualization
- Trade data export to CSV

## Usage Examples

### Basic Backtest Example

```python
from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from src.backtest import BacktestEngine

# Initialize components
client = BinanceClient(api_key="your_api_key", api_secret="your_api_secret", testnet=True)
market_data = MarketDataCollector(client)
strategy = MovingAverageCrossoverStrategy(market_data)

# Configure strategy
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

# Run backtest
performance = backtest_engine.run_backtest(
    strategy=strategy,
    symbols=["BTCUSDT", "ETHUSDT"],
    timeframe="1h",
    start_date="1 Jan, 2023",
    end_date="1 Jul, 2023",
    position_size_type="percentage",
    position_size_value=10.0,  # 10% of capital per position
    use_stop_loss=True,
    stop_loss_percentage=2.0,
    use_take_profit=True,
    take_profit_percentage=4.0
)

# Display results
performance.print_summary()
performance.plot_equity_curve()
performance.export_to_csv("backtest_results.csv")
```

### Real-time Trading Example

```python
from src.api.client import BinanceClient
from src.data.market_data import MarketDataCollector
from src.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from src.trading.realtime_trader import RealTimeTrader

# Initialize components
client = BinanceClient(api_key="your_api_key", api_secret="your_api_secret", testnet=True)
market_data = MarketDataCollector(client)
strategy = MovingAverageCrossoverStrategy(market_data)

# Configure strategy
strategy.set_params({
    "fast_ma_period": 9,
    "slow_ma_period": 21
})

# Initialize real-time trader (paper trading mode)
trader = RealTimeTrader(
    client=client,
    market_data=market_data,
    strategy=strategy,
    trading_mode="paper",  # use "live" for real trading
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

# Start trading
trader.start(["BTCUSDT", "ETHUSDT"], "1h")

# Get performance metrics after some time
metrics = trader.get_performance_metrics()
print(f"Win rate: {metrics['win_rate']}%")
print(f"Total P&L: {metrics['total_pnl']} ({metrics['total_pnl_percent']}%)")

# Stop trading when done
trader.stop()
trader.export_trades_to_csv("trading_results.csv")
```

## Command Line Interface

The `trading_cli.py` script provides a command-line interface to run backtests and real-time trading.

### Backtest Command

```bash
# Run a backtest with the MA Crossover strategy on BTC and ETH
python src/trading_cli.py backtest --strategy ma_crossover --symbols BTCUSDT,ETHUSDT --timeframe 1h

# Run a backtest with custom parameters
python src/trading_cli.py backtest --strategy fibobull --symbols BTCUSDT --timeframe 4h --start-date "1 Jan, 2023" --end-date "1 Jul, 2023" --capital 5000 --stop-loss 1.5 --take-profit 3.0
```

### Real-time Trading Command

```bash
# Run paper trading with the MA Crossover strategy
python src/trading_cli.py trading --strategy ma_crossover --symbols BTCUSDT,ETHUSDT --timeframe 1h --mode paper

# Run live trading with custom parameters
python src/trading_cli.py trading --strategy fibobull --symbols BTCUSDT --timeframe 15m --mode live --size-value 2.0 --stop-loss 1.0 --check-interval 30
```

## Risk Warning

When using the live trading mode, real funds will be at risk. Always test your strategies thoroughly with the backtest module and paper trading before using real funds.

## Dependencies

- Python 3.7+
- pandas
- numpy
- matplotlib
- python-binance
- loguru 
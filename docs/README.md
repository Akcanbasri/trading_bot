# Binance Trading Bot

A modular trading bot using the Binance API, following SOLID and DRY principles.

## Project Structure

```
trading_bot/
├── src/                      # Source code
│   ├── api/                  # Binance API integration
│   ├── config/               # Configuration settings
│   ├── data/                 # Data fetching and processing
│   ├── indicators/           # Technical indicators
│   ├── order_management/     # Order management
│   ├── risk_management/      # Risk management
│   ├── signals/              # Signal generation and control
│   ├── strategies/           # Trading strategies
│   └── utils/                # Utility functions
├── tests/                    # Test files
├── docs/                     # Documentation
└── logs/                     # Log files
```

## Installation

```bash
# Install required libraries
pip install -r requirements.txt
```

## Usage

```bash
python -m src.main
```

## Long and Short Conditions

The bot opens long and short positions using two different strategies:

### 1. Moving Average Crossover Strategy

- **Long (Buy) Conditions:**
  - Short-term moving average crosses above long-term moving average
  - Short-term moving average is above long-term moving average and signal strength is greater than 1.0

- **Short (Sell) Conditions:**
  - Short-term moving average crosses below long-term moving average
  - Short-term moving average is below long-term moving average and signal strength is less than -1.0

### 2. FiboBULL Strategy

- **Long (Buy) Conditions:**
  - When FiboBULL PA indicator gives a "BUY" signal
  - When an upward trend is detected

- **Short (Sell) Conditions:**
  - When FiboBULL PA indicator gives a "SELL" signal
  - When a downward trend is detected

### Position Closing Conditions

For both strategies, positions are closed under the following conditions:

1. **Stop-Loss:** When price reaches the specified stop-loss level
2. **Take-Profit:** When price reaches the specified take-profit level
3. **Signal Change:** 
   - When a "SELL" signal is received while in a long position
   - When a "BUY" signal is received while in a short position

### Risk Management

- Minimum 5 USDT position size check for each trade
- Maximum position size limited to 3% of account balance
- Daily maximum loss limit of 3% of account balance
- Total maximum loss limit of 15% of account balance 